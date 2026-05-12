from prefect import flow, task
from src.services.crawler.crawl import Crawler
from src.services.job_processor.job_processor import JobProcessor
from src.infrastructure.logging import configure_logging, get_logger
import asyncio
import uuid

logger = get_logger(__name__)

@task(retries=3, retry_delay_seconds=60)
async def fetch_links_task(run_id: str):
    logger.info("Task: Fetching job links")
    crawler = Crawler()
    links = await crawler.fetch_job_links(run_id)
    return links

@task(retries=2, retry_delay_seconds=300)
async def crawl_jobs_task(links, run_id: str):
    if not links:
        logger.info("No new links to crawl.")
        return
    logger.info(f"Task: Crawling {len(links)} jobs")
    crawler = Crawler()
    await crawler.crawl_jobs(links, run_id)

@task
def process_jobs_task(limit: int):
    logger.info("Task: Processing unstructured jobs")
    processor = JobProcessor()
    processor.process_jobs(limit=limit)

@flow(name="Job Ingestion Flow")
async def job_ingestion_flow(limit: int = 20):
    configure_logging()
    run_id = str(uuid.uuid4())[:8]
    
    # 1. Fetch
    new_links = await fetch_links_task(run_id)
    
    # 2. Crawl
    if new_links:
        await crawl_jobs_task(new_links, run_id)
        
        # 3. Process (Structured + Vectorize)
        # We only process if we actually crawled something
        process_jobs_task(limit=limit)
    else:
        logger.info("Pipeline finished: No new jobs found today.")

if __name__ == "__main__":
    asyncio.run(job_ingestion_flow(limit=10))
