import asyncio
import uuid

from prefect import flow, task

from src.core.models.fetch_result import FetchOutcome, FetchStatus
from src.internhunter.common.logging import configure_logging, get_logger
from src.internhunter.storage.repositories.etl import ETLRepository
from src.internhunter.ingestion.crawl import Crawler
from src.internhunter.extraction.job_processor import JobProcessor

logger = get_logger(__name__)


@task(retries=3, retry_delay_seconds=60)
async def fetch_links_task(run_id: str, limit: int | None = None) -> FetchOutcome:
    logger.info("Task: Fetching job links")
    crawler = Crawler()
    return await crawler.fetch_job_links(run_id, limit=limit)


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

    repo = ETLRepository()
    repo.create_tables()

    outcome = await fetch_links_task(run_id, limit=limit)
    logger.info(
        "Fetch links completed",
        run_id=run_id,
        limit=limit,
        status=outcome.status.value,
        links_returned=outcome.new_count,
        pages_scraped=outcome.pages_scraped,
        total_scraped=outcome.total_scraped,
    )

    if outcome.is_success and outcome.links:
        crawl_links = outcome.links[:limit] if limit is not None else outcome.links
        extracted, extract_failed = await crawl_jobs_task(crawl_links, run_id)
        processed, process_failed = await process_jobs_task(limit=limit)

        repo.save_pipeline_run_summary(
            run_id=run_id,
            acquired=outcome.new_count,
            processed=processed,
            failed=process_failed,
        )
        logger.info(
            "Pipeline finished successfully.",
            run_id=run_id,
            acquired=outcome.new_count,
            extracted=extracted,
            extract_failed=extract_failed,
            processed=processed,
            pages_scraped=outcome.pages_scraped,
        )
    elif not outcome.is_success:
        logger.info(
            "Skipping crawl and process because fetch links did not succeed.",
            run_id=run_id,
            limit=limit,
            status=outcome.status.value,
            error=outcome.error,
        )
    else:
        status_label = outcome.status.value
        logger.info(
            "Skipping crawl and process because no new links were available after dedup.",
            run_id=run_id,
            reason=status_label,
            limit=limit,
            links_returned=outcome.new_count,
            total_scraped=outcome.total_scraped,
            pages_scraped=outcome.pages_scraped,
        )

        repo.save_pipeline_run_summary(
            run_id=run_id,
            acquired=outcome.total_scraped,
            processed=0,
            failed=0,
            status="blocked" if outcome.status == FetchStatus.BLOCKED else "completed",
        )


if __name__ == "__main__":
    asyncio.run(job_ingestion_flow(limit=10))


__all__ = ["fetch_links_task", "crawl_jobs_task", "process_jobs_task", "job_ingestion_flow"]
