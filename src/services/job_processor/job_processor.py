import time

from src.infrastructure.llm.router import llm_router
from src.infrastructure.db.repository import JobRepository
from src.services.job_processor.embedder import Embedder
from src.config.settings import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class JobProcessor():

    def __init__(self):
        self.router = llm_router
        self.embedder = Embedder()

    def _build_embedding_text(self, parsed_result) -> str:
        """Build a text representation of the parsed job for embedding."""
        parts = []
        if parsed_result.standardized_title:
            parts.append(parsed_result.standardized_title)
        if parsed_result.description:
            parts.append(parsed_result.description)
        if parsed_result.technical_competencies:
            parts.append(", ".join(parsed_result.technical_competencies))
        return "\n".join(parts)

    def process_jobs(self, limit: int = 100):
        logger.info("Job processing cycle starting", limit=limit)

        from src.services.job_processor.validator import JobValidator
        validator = JobValidator()
        repo = JobRepository()
        
        # Use new production-grade fetch
        jobs = repo.fetch_pending_raw_jobs(limit=limit)

        success_count = 0
        fail_count = 0

        rate_limit = settings.config_yaml.get("crawler", {}).get("rate_limit_rpm", 20)
        for job in jobs:
            if rate_limit > 0:
                sleep_time = 60 / rate_limit
                time.sleep(sleep_time)

            try:
                # Step 1: Validation Guardrail (Heuristics + LLM-Lite)
                raw_text = job.raw_markdown or str(job.full_json_dump)
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

        logger.info("Batch completed", success=success_count, failed=fail_count)

def run_pipeline(limit: int = 10):
    processor = JobProcessor()
    processor.process_jobs(limit=limit)
