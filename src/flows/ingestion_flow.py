from prefect import flow, task
from src.services.crawler.crawl import Crawler
from src.services.job_processor.job_processor import JobProcessor
from src.core.models.fetch_result import FetchOutcome, FetchStatus
from src.infrastructure.logging import configure_logging, get_logger
from src.infrastructure.db.repositories.etl import ETLRepository
import asyncio
import uuid

logger = get_logger(__name__)

@task(retries=3, retry_delay_seconds=60)
async def fetch_links_task(run_id: str) -> FetchOutcome:
    logger.info("Task: Fetching job links")
    crawler = Crawler()
    return await crawler.fetch_job_links(run_id)

@task(retries=2, retry_delay_seconds=300)
async def crawl_jobs_task(links, run_id: str) -> tuple[int, int]:
    if not links:
        logger.info("No new links to crawl.")
        return 0, 0
    logger.info(f"Task: Crawling {len(links)} jobs")
    crawler = Crawler()
    return await crawler.crawl_jobs(links, run_id)

@task
async def process_jobs_task(limit: int):
    logger.info("Task: Processing unstructured jobs")
    processor = JobProcessor()
    return await processor.process_jobs(limit=limit)

@flow(name="Job Ingestion Flow")
async def job_ingestion_flow(limit: int = 20):
    configure_logging()
    run_id = str(uuid.uuid4())[:8]
    
    # 0. Ensure database tables exist
    repo = ETLRepository()
    repo.create_tables()

    # 1. Fetch (returns typed FetchOutcome)
    outcome = await fetch_links_task(run_id)
    
    if outcome.is_success and outcome.links:
        # 2. Crawl (returns extraction counts)
        extracted, extract_failed = await crawl_jobs_task(outcome.links, run_id)
        
        # 3. Process (Structured + Vectorize)
        processed, process_failed = process_jobs_task(limit=limit)
        
        # 4. Save Telemetry
        repo.save_pipeline_run_summary(
            run_id=run_id,
            acquired=outcome.new_count,
            processed=processed,
            failed=process_failed
        )
        logger.info("Pipeline finished successfully.",
                     run_id=run_id, acquired=outcome.new_count,
                     extracted=extracted, extract_failed=extract_failed,
                     processed=processed, pages_scraped=outcome.pages_scraped)
    else:
        # Differentiate failure reasons in telemetry
        status_label = outcome.status.value  # "blocked", "network_fail", "no_new", etc.
        logger.info("Pipeline finished without processing.",
                     run_id=run_id, reason=status_label,
                     total_scraped=outcome.total_scraped,
                     pages_scraped=outcome.pages_scraped,
                     error=outcome.error)
        
        repo.save_pipeline_run_summary(
            run_id=run_id,
            acquired=outcome.total_scraped,
            processed=0,
            failed=0,
            status="blocked" if outcome.status == FetchStatus.BLOCKED else "completed"
        )

if __name__ == "__main__":
    asyncio.run(job_ingestion_flow(limit=10))
