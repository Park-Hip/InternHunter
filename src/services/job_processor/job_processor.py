import time

from src.infrastructure.llm.router import llm_router
from src.infrastructure.db.repository import JobRepository
from src.config import settings
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class JobProcessor():

    def __init__(self):
        self.llm = llm_router.get_client()

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
                # Assuming llm.parse_raw_job returns a StandardJob or similar
                # We need to make sure 'self.llm' is mocked or compatible.
                # Assuming existing code structure is compatible with new models if types match.
                parsed_result = self.llm.process_raw_job(job)

                if repo.save_parsed_job(parsed_result, job.id, job.url):
                    success_count += 1
                    logger.info("Parsed job saved", job_title=job.title)

                else:
                    fail_count += 1
                
            except Exception as e:
                logger.error("Job processing failed", job_id=job.id, error=str(e), exc_info=True)
                fail_count += 1

        logger.info("Batch completed", success=success_count, failed=fail_count)

def run_pipeline(limit: int = 10):
    processor = JobProcessor()
    processor.process_jobs(limit=limit)



