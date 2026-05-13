from typing import List

from prefect import task

from src.internhunter.storage.repositories.etl import ETLRepository
from src.internhunter.common.logging import get_logger
from src.internhunter.ingestion.crawl import Crawler
from src.internhunter.extraction.job_processor import JobProcessor

logger = get_logger(__name__)


@task(retries=3, retry_delay_seconds=60)
async def fetch_job_links_task(run_id: str, url: str, limit: int | None = None, force_recrawl: bool = False) -> List[dict]:
    """Fetches job URLs from the search page."""
    crawler = Crawler()
    links = await crawler.fetch_job_links(run_id, limit=limit, force_recrawl=force_recrawl)
    return links or []


@task(retries=2, retry_delay_seconds=30)
async def acquire_job_task(url: str, run_id: str) -> bool:
    """Acquires a single job (CSS or RAW fallback) and saves to staging."""
    from crawl4ai import AsyncWebCrawler
    from src.internhunter.ingestion.crawl_config import browser_config
    from crawl4ai.browser_adapter import UndetectedAdapter

    repo = ETLRepository()
    crawler_service = Crawler()

    adapter = UndetectedAdapter()
    async with AsyncWebCrawler(config=browser_config, browser_adapter=adapter) as crawler:
        job_data = await crawler_service.extract_single_job(crawler, url)

        if job_data:
            job_to_save = {
                "url": url,
                "crawl_run_id": run_id,
                "title": job_data.get("title"),
                "company": job_data.get("company"),
                "location": job_data.get("location"),
                "full_json_dump": job_data.get("full_json_dump"),
                "status": job_data.get("status", "pending"),
                "extraction_method": job_data.get("extraction_method", "css"),
                "raw_markdown": job_data.get("raw_markdown"),
            }

            if repo.save_raw_job(job_to_save):
                if job_data.get("status") == "blocked":
                    repo.save_to_audit(
                        {
                            "url": url,
                            "error_type": "BOT_DETECTED",
                            "error_message": "Blocked by captcha/verification",
                            "screenshot_path": crawler_service._save_screenshot(job_data.get("screenshot"), url),
                            "html_content": job_data.get("html"),
                        }
                    )
                return True
        else:
            repo.save_to_audit(
                {
                    "url": url,
                    "error_type": "CRAWL_FAILED",
                    "error_message": "Crawler returned None after retries",
                }
            )
            return False


@task
async def process_pending_jobs_task(limit: int = 100, skip_llm_validation: bool = False, crawl_run_id: str | None = None):
    """Orchestrates Validation, Transformation, and Loading for all pending jobs."""
    processor = JobProcessor()
    await processor.process_jobs(limit=limit, skip_llm_validation=skip_llm_validation, crawl_run_id=crawl_run_id)


__all__ = ["fetch_job_links_task", "acquire_job_task", "process_pending_jobs_task"]
