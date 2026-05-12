import json
import random
import os
import base64
import hashlib
import time
import asyncio
from datetime import datetime
from typing import Any, List
from prefect import task

from src.config.settings import settings
from src.infrastructure.db.repositories.etl import ETLRepository
from src.infrastructure.logging import get_logger, bind_context
from src.services.crawler.crawl import Crawler
from src.services.job_processor.job_processor import JobProcessor
from src.services.job_processor.validator import JobValidator
from src.core.models.job import RawJob

logger = get_logger(__name__)

@task(retries=3, retry_delay_seconds=60)
async def fetch_job_links_task(run_id: str, url: str) -> List[dict]:
    """Fetches job URLs from the search page."""
    crawler = Crawler()
    links = await crawler.fetch_job_links(run_id)
    return links or []

@task(retries=2, retry_delay_seconds=30)
async def acquire_job_task(url: str, run_id: str) -> bool:
    """Acquires a single job (CSS or RAW fallback) and saves to staging."""
    from crawl4ai import AsyncWebCrawler
    from src.services.crawler.crawl_config import browser_config
    from crawl4ai.browser_adapter import UndetectedAdapter
    
    repo = ETLRepository()
    crawler_service = Crawler()
    
    adapter = UndetectedAdapter()
    async with AsyncWebCrawler(config=browser_config, browser_adapter=adapter) as crawler:
        job_data = await crawler_service.extract_single_job(crawler, url)
        
        if job_data:
            job_to_save = {
                "url": url,
                "title": job_data.get("title"),
                "company": job_data.get("company"),
                "location": job_data.get("location"),
                "full_json_dump": job_data.get("full_json_dump"),
                "status": job_data.get("status", "pending"),
                "extraction_method": job_data.get("extraction_method", "css"),
                "raw_markdown": job_data.get("raw_markdown")
            }

            if repo.save_raw_job(job_to_save):
                # Handle immediate audit if blocked
                if job_data.get("status") == "blocked":
                     repo.save_to_audit({
                         "url": url,
                         "error_type": "BOT_DETECTED",
                         "error_message": "Blocked by captcha/verification",
                         "screenshot_path": crawler_service._save_screenshot(job_data.get("screenshot"), url),
                         "html_content": job_data.get("html")
                     })
                return True
        else:
            # Total failure
            repo.save_to_audit({
                "url": url,
                "error_type": "CRAWL_FAILED",
                "error_message": "Crawler returned None after retries"
            })
            return False

@task
async def process_pending_jobs_task(limit: int = 100):
    """Orchestrates Validation, Transformation, and Loading for all pending jobs."""
    processor = JobProcessor()
    await processor.process_jobs(limit=limit)
