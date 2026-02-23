import time

from src.infrastructure.llm.router import llm_router
from src.infrastructure.db.repository import JobRepository
from src.services.job_processor.embedder import Embedder
from src.config import settings
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

        repo = JobRepository()
        jobs = repo.fetch_unparsed_jobs(limit=limit)

        success_count = 0
        fail_count = 0

        for job in jobs:
            if settings.RATE_LIMIT_RPM > 0:
                sleep_time = 60 / settings.RATE_LIMIT_RPM
                time.sleep(sleep_time)

            try:
                # Step 1: Parse the job with LLM (Gemini -> Groq fallback)
                parsed_result = self.router.process_with_fallback(job)

                # Step 2: Generate embedding from parsed content
                embedding = None
                text_to_embed = self._build_embedding_text(parsed_result)
                if text_to_embed.strip():
                    try:
                        embedding = self.embedder.generate_embedding(text_to_embed)
                        logger.info("Embedding generated", job_title=job.title)
                    except Exception as e:
                        logger.warning("Embedding failed, saving job without it", job_id=job.id, error=str(e))

                # Step 3: Save parsed job + embedding together
                if repo.save_parsed_job(parsed_result, job.id, job.url, embedding=embedding):
                    success_count += 1
                    logger.info("Parsed job saved", job_title=job.title, has_embedding=embedding is not None)
                else:
                    fail_count += 1
                
            except Exception as e:
                logger.error("Job processing failed", job_id=job.id, error=str(e), exc_info=True)
                fail_count += 1

        logger.info("Batch completed", success=success_count, failed=fail_count)

def run_pipeline(limit: int = 10):
    processor = JobProcessor()
    processor.process_jobs(limit=limit)
