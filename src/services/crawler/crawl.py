import asyncio
import json
import random
import os
import base64
import hashlib
import time
import uuid
from datetime import datetime
from typing import Any

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.infrastructure.db.repository import JobRepository
from src.infrastructure.logging import get_logger, configure_logging, bind_context, clear_context
from src.services.crawler.crawl_config import (
    browser_config,
    fetch_link_run_config,
    extract_detail_run_config
)

from crawl4ai import AsyncWebCrawler
from crawl4ai.browser_adapter import UndetectedAdapter

logger = get_logger(__name__)

# Retry on transient network/IO errors only (do not retry on block/captcha - those are in result)
RETRY_EXCEPTIONS = (ConnectionError, OSError, asyncio.TimeoutError, TimeoutError)

class Crawler:
    def __init__(self):
        self.fetch_link_url = settings.DS_URL

    async def _arun_with_retry(self, crawler, url, config, max_attempts=None):
        """Call crawler.arun with exponential backoff. Raises after max_attempts on network/IO errors."""
        if max_attempts is None:
            max_attempts = settings.config_yaml.get("crawler", {}).get("max_retries", 3)
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type(RETRY_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                return await crawler.arun(url=url, config=config)

    @staticmethod
    def normalize_url(url: str) -> str:
        """Canonical URL for dedup (strip query/fragment and whitespace)."""
        if not url or not isinstance(url, str):
            return ""
        return url.split("?")[0].split("#")[0].strip()

    async def fetch_job_links(self, run_id: str) -> list[dict] | None:
        """Fetches job URLs from the search page."""
        bind_context(run_id=run_id)

        logger.info("Fetch links phase starting", phase="fetch_links", status="start")

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info("Fetching job links", phase="fetch_links", url=self.fetch_link_url)
                await asyncio.sleep(random.uniform(2, 4))

                result = await self._arun_with_retry(crawler, self.fetch_link_url, fetch_link_run_config)

                if result.success:
                    if "Verify you are human" in result.html or "Just a moment" in result.html:
                        logger.warning("Blocked by captcha/verification", phase="fetch_links", status="block", url=self.fetch_link_url)
                        return None

                    data = json.loads(result.extracted_content)
                    logger.info("Jobs found", count=len(data))

                    formatted_links = []
                    for item in data:
                        raw_url = item.get("url") or ""
                        normalized = self.normalize_url(raw_url)
                        if normalized:
                            formatted_links.append({
                                "url": normalized,
                                "scraped_at": datetime.now().isoformat(),
                                "source": "topcv"
                            })

                    repo = JobRepository()
                    new_links = repo.filter_new_links(formatted_links)

                    logger.info(
                        "Links filtered",
                        phase="fetch_links",
                        total=len(formatted_links),
                        new=len(new_links)
                    )

                    if not new_links:
                        logger.info("Fetch links completed", phase="fetch_links", status="done", reason="no_new_jobs")
                        return None
                    
                    return new_links
                else:
                    logger.error("Fetch links failed", phase="fetch_links", status="fail", error=result.error_message)
                    return None

        except Exception as e:
            logger.error("Fetch links exception", phase="fetch_links", status="error", error=str(e), exc_info=True)
            return None

        finally:
            clear_context()

    async def extract_single_job(self, crawler: AsyncWebCrawler, url: str) -> dict[str, Any] | None:
        delay = random.uniform(10, 15)
        logger.info("Waiting before extraction", delay_seconds=round(delay, 1), url=url)
        await asyncio.sleep(delay)

        try:
            result = await self._arun_with_retry(crawler, url, extract_detail_run_config)

            if not result.success:
                logger.error("Network/crawl failed", url=url, error=result.error_message)
                return None

            # 1. Try CSS extraction
            data = None
            if result.extracted_content:
                try:
                    data = json.loads(result.extracted_content)
                    if isinstance(data, list) and data:
                        data = data[0]
                except Exception:
                    data = None

            # Check if CSS extraction was successful and high quality
            is_valid_css = (
                isinstance(data, dict) and 
                data.get('title') and 
                data.get('info') and 
                len(str(data.get('info'))) > 200
            )
            
            if is_valid_css:
                logger.info("CSS extraction successful", url=url)
                title = data.get('title', '').strip()
                company = data.get('company', '').strip()
                return {
                    "url": url,
                    "title": title,
                    "company": company,
                    "location": data.get('location', '').strip(),
                    "full_json_dump": data,
                    "extraction_method": "css",
                    "status": "pending"
                }
            else:
                # 2. Fallback to RAW Markdown
                logger.warning("CSS extraction failed/poor quality, using RAW fallback", url=url)
                
                # Check for blocking
                html = (result.html or "")
                is_blocked = "Verify you are human" in html or "Just a moment" in html
                
                return {
                    "url": url,
                    "title": "Unknown (RAW)",
                    "company": "Unknown (RAW)",
                    "location": "Unknown",
                    "raw_markdown": result.markdown_v2.raw_markdown if result.markdown_v2 else result.markdown,
                    "extraction_method": "raw",
                    "status": "blocked" if is_blocked else "pending",
                    "screenshot": result.screenshot,
                    "html": result.html,
                    "full_json_dump": {"error": "CSS extraction failed", "is_blocked": is_blocked}
                }

        except Exception as e:
            logger.error("Extraction error", url=url, error=str(e), exc_info=True)
            return None

        except Exception as e:
            logger.error("Extraction error", url=url, error=str(e), exc_info=True)
            return None

    def _save_screenshot(self, screenshot_b64: str | None, url: str) -> str | None:
        if not screenshot_b64:
            return None
        try:
            safe_id = hashlib.md5(url.encode()).hexdigest()
            os.makedirs("errors", exist_ok=True)
            img_path = f"errors/error_{safe_id}_{int(time.time())}.png"
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(screenshot_b64))
            return img_path
        except Exception as e:
            logger.warning("Failed to save screenshot", error=str(e))
            return None

    async def crawl_jobs(self, new_links, run_id: str) -> None:
        """"Crawl new_links fetched by fetch_job_links()"""

        bind_context(run_id=run_id)
        if not new_links:
            logger.error("Extract phase skipped", phase="extract", status="skip", reason="no_links")
            return

        repo = JobRepository()
        raw_jobs_count = repo.get_raw_jobs_count()
        remaining_links = repo.filter_new_links(new_links)

        new_links_count = len(new_links)
        already_in_db = new_links_count - len(remaining_links)

        logger.info(
            "Extract phase starting",
            phase="extract",
            status="start",
            db_raw_jobs=raw_jobs_count,
            links_from_file=new_links_count,
            already_in_db=already_in_db,
            remaining=len(remaining_links)
        )

        if not remaining_links:
            logger.info("Extract phase completed", phase="extract", status="done", reason="no_remaining_links")
            return

        start_time = time.monotonic()
        saved_count = 0
        failed_count = 0

        adapter = UndetectedAdapter()
        async with AsyncWebCrawler(config=browser_config, browser_adapter=adapter) as crawler:
            for i, link_record in enumerate(remaining_links):
                logger.info(
                    "Processing job",
                    phase="extract",
                    progress=f"{i + 1}/{len(remaining_links)}",
                    url=link_record["url"]
                )

                job_data = await self.extract_single_job(crawler, link_record["url"])

                if job_data:
                    # Prepare data for repository
                    job_to_save = {
                        "url": link_record["url"],
                        "title": job_data.get("title"),
                        "company": job_data.get("company"),
                        "location": job_data.get("location"),
                        "full_json_dump": job_data.get("full_json_dump"),
                        "status": job_data.get("status", "pending"),
                        "extraction_method": job_data.get("extraction_method", "css"),
                        "raw_markdown": job_data.get("raw_markdown")
                    }

                    if repo.save_raw_job(job_to_save):
                        saved_count += 1
                        
                        # Handle immediate audit if blocked
                        if job_data.get("status") == "blocked":
                             repo.save_to_audit({
                                 "url": link_record["url"],
                                 "error_type": "BOT_DETECTED",
                                 "error_message": "Blocked by captcha/verification",
                                 "screenshot_path": self._save_screenshot(job_data.get("screenshot"), link_record["url"]),
                                 "html_content": job_data.get("html")
                             })
                    else:
                        failed_count += 1
                        logger.warning("Database save failed", phase="extract", url=link_record["url"], status="db_fail")

                else:
                    failed_count += 1
                    logger.info("Extraction failed completely", phase="extract", url=link_record["url"], status="extract_fail")
                    # If it totally failed (result.success=False), add to audit
                    repo.save_to_audit({
                        "url": link_record["url"],
                        "error_type": "CRAWL_FAILED",
                        "error_message": "Crawler returned result.success=False after retries"
                    })

        duration_sec = time.monotonic() - start_time
        logger.info(
            "Extract phase completed",
            phase="extract",
            status="done",
            total=len(remaining_links),
            saved=saved_count,
            failed=failed_count,
            duration_sec=round(duration_sec, 1)
        )


async def run_crawler_pipeline(run_id: str):
    """Main pipeline entry point."""
    crawler = Crawler()
    new_links = await crawler.fetch_job_links(run_id)
    if new_links:
        await crawler.crawl_jobs(new_links, run_id)


if __name__ == "__main__":

    configure_logging()
    
    run_id = str(uuid.uuid4())[:8]
    logger.info("Crawler pipeline starting", run_id=run_id)

    asyncio.run(run_crawler_pipeline(run_id))
