import asyncio
import json
import time

from src.internhunter.llm.router import llm_router
from src.infrastructure.db.repositories.etl import ETLRepository
from src.internhunter.embeddings.embedder import Embedder
from src.config.settings import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

_VALIDATION_PRIORITY_KEYS = (
    "title",
    "company",
    "location",
    "salary",
    "experience",
    "info",
    "description",
    "requirement",
    "benefit",
)
_VALIDATION_NOISY_KEYS = {
    "error",
    "is_blocked",
    "blocked_reason",
    "retry_count",
    "status",
    "extraction_method",
    "created_at",
    "updated_at",
}


def _iter_useful_text(value, *, key: str | None = None, depth: int = 0, max_depth: int = 4):
    """Yield readable text fragments from nested job payloads."""
    if value is None or depth > max_depth:
        return

    if isinstance(value, str):
        text = value.strip()
        if text:
            try:
                parsed = json.loads(text)
            except Exception:
                yield text
            else:
                if isinstance(parsed, (dict, list)):
                    yield from _iter_useful_text(parsed, key=key, depth=depth + 1, max_depth=max_depth)
                else:
                    parsed_text = str(parsed).strip()
                    if parsed_text:
                        yield parsed_text
        return

    if isinstance(value, (int, float, bool)):
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_useful_text(item, key=key, depth=depth + 1, max_depth=max_depth)
        return

    if isinstance(value, dict):
        keys = list(value.keys())
        ordered_keys = [k for k in _VALIDATION_PRIORITY_KEYS if k in value]
        ordered_keys.extend(
            k for k in keys
            if k not in ordered_keys and k not in _VALIDATION_NOISY_KEYS
        )

        for child_key in ordered_keys:
            yield from _iter_useful_text(
                value.get(child_key),
                key=child_key,
                depth=depth + 1,
                max_depth=max_depth,
            )


def build_validation_text(job) -> str:
    """Build readable validation text from raw job fields and extracted payloads."""
    parts = []

    for field_name in ("title", "company", "location"):
        value = getattr(job, field_name, None)
        if value:
            text = str(value).strip()
            if text:
                parts.append(text)

    raw_markdown = getattr(job, "raw_markdown", None)
    if raw_markdown:
        raw_text = str(raw_markdown).strip()
        if raw_text:
            parts.append(raw_text)

    full_json_dump = getattr(job, "full_json_dump", None)
    if full_json_dump:
        for fragment in _iter_useful_text(full_json_dump):
            if fragment and fragment not in parts:
                parts.append(fragment)

    return "\n".join(parts)


class JobProcessor():

    def __init__(self):
        self.router = llm_router
        self.embedder = Embedder()

    def _build_embedding_text(self, parsed_result) -> str:
        """
        Build a rich text representation of the parsed job for embedding.
        """
        parts = []
        if parsed_result.standardized_title:
            parts.append(f"Title: {parsed_result.standardized_title}")
        if parsed_result.job_level:
            parts.append(f"Level: {parsed_result.job_level}")
        if parsed_result.cities:
            parts.append(f"Location: {', '.join(parsed_result.cities)}")
        if parsed_result.description:
            parts.append(parsed_result.description)
        if parsed_result.requirement:
            parts.append(parsed_result.requirement)
        if parsed_result.tech_stack:
            parts.append(f"Tech Stack: {', '.join(parsed_result.tech_stack)}")
        if parsed_result.technical_competencies:
            parts.append(f"Competencies: {', '.join(parsed_result.technical_competencies)}")
        if parsed_result.domain_knowledge:
            parts.append(f"Domain: {', '.join(parsed_result.domain_knowledge)}")
        return "\n".join(parts)

    async def process_jobs(self, limit: int = 100, skip_llm_validation: bool = False):
        """Process pending raw jobs through validation, LLM transformation, embedding, and loading.
        
        Async with smart rate limiting: only sleeps the remaining interval after
        accounting for actual LLM processing time.
        
        Returns:
            (success_count, fail_count)
        """
        logger.info("Job processing cycle starting", limit=limit, skip_llm_validation=skip_llm_validation)
        if skip_llm_validation:
            logger.warning("LLM validation skipped in local/dev mode", limit=limit)

        from src.services.job_processor.validator import JobValidator
        validator = JobValidator()
        repo = ETLRepository()
        
        # Use new production-grade fetch
        jobs = repo.fetch_pending_raw_jobs(limit=limit)
        logger.info(
            "Pending raw jobs selected",
            limit=limit,
            count=len(jobs),
            raw_job_ids=[job.id for job in jobs],
            urls=[job.url for job in jobs],
            retry_counts=[job.retry_count for job in jobs],
        )

        success_count = 0
        fail_count = 0

        # Smart rate limiting: only sleep the remaining time after LLM call
        llm_rpm = settings.config_yaml.get("llm", {}).get("rate_limit_rpm", 20)
        min_interval = 60.0 / llm_rpm if llm_rpm > 0 else 0

        for job in jobs:
            iteration_start = time.monotonic()

            try:
                # Step 1: Validation Guardrail (Heuristics + LLM-Lite)
                raw_text = build_validation_text(job)
                if skip_llm_validation:
                    if not validator.heuristic_check(raw_text):
                        is_valid = False
                        reason = "Heuristic check failed: text too short or lacks job keywords."
                    else:
                        is_valid = True
                        reason = "LLM validation skipped in local/dev mode"
                else:
                    is_valid, reason = validator.is_valid(raw_text)
                
                if not is_valid:
                    logger.warning("Job rejected by validator", url=job.url, reason=reason)
                    repo.update_job_status(job.id, "failed")
                    repo.save_to_audit({
                        "url": job.url,
                        "error_type": "VALIDATION_FAILED",
                        "error_message": reason,
                        "html_content": raw_text[:10000] # Store snippet of raw data
                    })
                    fail_count += 1
                    continue

                # Step 2: Parse the job with LLM (Gemini -> Groq fallback)
                logger.info("Transforming job", url=job.url, method=job.extraction_method)
                parsed_result = self.router.process_with_fallback(job)
                
                # Step 3: Strict Quality Gate (Post-Parse)
                # Verify critical fields exist
                if not parsed_result.standardized_title or not parsed_result.description:
                    logger.error("LLM failed to extract critical fields", url=job.url)
                    repo.update_job_status(job.id, "failed")
                    repo.save_to_audit({
                        "url": job.url,
                        "error_type": "LLM_INCOMPLETE",
                        "error_message": "Missing critical fields (title/description) in LLM output"
                    })
                    fail_count += 1
                    continue

                # Step 4: Generate embedding from parsed content
                embedding = None
                text_to_embed = self._build_embedding_text(parsed_result)
                if text_to_embed.strip():
                    try:
                        embedding = self.embedder.generate_embedding(text_to_embed)
                        logger.info("Embedding generated", job_title=job.title)
                    except Exception as e:
                        logger.warning("Embedding failed", job_id=job.id, error=str(e))

                # Step 5: Save parsed job + embedding together
                if repo.save_parsed_job(parsed_result, job.id, job.url, embedding=embedding):
                    repo.update_job_status(job.id, "completed")
                    success_count += 1
                    logger.info("Parsed job saved", job_title=job.title, has_embedding=embedding is not None)
                else:
                    repo.update_job_status(job.id, "failed")
                    fail_count += 1
                
            except Exception as e:
                logger.error("Job processing failed", job_id=job.id, error=str(e), exc_info=True)
                repo.update_job_status(job.id, "failed")
                repo.save_to_audit({
                    "url": job.url,
                    "error_type": "PROCESSING_ERROR",
                    "error_message": str(e)
                })
                fail_count += 1

            # Smart rate limiting: only sleep the remaining interval
            elapsed = time.monotonic() - iteration_start
            if min_interval > 0 and elapsed < min_interval:
                sleep_time = min_interval - elapsed
                await asyncio.sleep(sleep_time)

        logger.info("Batch completed", success=success_count, failed=fail_count)
        return success_count, fail_count

async def run_pipeline(limit: int = 10):
    processor = JobProcessor()
    await processor.process_jobs(limit=limit)
