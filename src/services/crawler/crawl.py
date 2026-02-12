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

from src.config import settings
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
        self.fetch_link_url = settings.URL

    async def _arun_with_retry(self, crawler, url, config, max_attempts=3):
        """Call crawler.arun with exponential backoff. Raises after max_attempts on network/IO errors."""
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

            data = json.loads(result.extracted_content)

            is_empty = not data or (isinstance(data, list) and not data)
            missing_critical = False

            if isinstance(data, list) and data:
                data = data[0]
            if not isinstance(data, dict):
                logger.warning("Extract failed", url=url, failure_reason="non_dict_payload")
                return None

            critical_fields = ['title', 'info']
            for key in critical_fields:
                if not data.get(key):
                    logger.error("Missing critical field", field=key, url=url)
                    missing_critical = True

            if is_empty or missing_critical:
                # Distinguish block/captcha vs selector/layout failure for easier debugging
                html = (result.html or "")
                failure_reason = (
                    "block"
                    if ("Verify you are human" in html or "Just a moment" in html)
                    else ("selector_empty" if is_empty else "missing_fields")
                )
                logger.warning(
                    "Extraction failed",
                    url=url,
                    failure_reason=failure_reason,
                    is_empty=is_empty,
                    missing_critical=missing_critical
                )

                safe_id = hashlib.md5(url.encode()).hexdigest()
                os.makedirs("errors", exist_ok=True)

                if result.screenshot:
                    img_path = f"errors/error_{safe_id}.png"
                    with open(img_path, "wb") as f:
                        f.write(base64.b64decode(result.screenshot))
                    logger.info("Error screenshot saved", path=img_path)

                html_path = f"errors/error_{safe_id}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(result.html)

                return None

            title = data.get('title')
            company = data.get('company')

            if title:
                title = title.strip()
            if company:
                company = company.strip()

            logger.info("Job extracted", title=title, company=company, url=url)

            data['url'] = url
            return data

        except Exception as e:
            logger.error("Extraction error", url=url, error=str(e), exc_info=True)
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
                        "full_json_dump": job_data # Store the entire scraped dict as JSON
                    }

                    if repo.save_raw_job(job_to_save):
                        saved_count += 1
                    else:
                        failed_count += 1
                        logger.warning("Database save failed", phase="extract", url=link_record["url"], status="db_fail")

                else:
                    failed_count += 1
                    logger.info("Extraction failed, cooling down", phase="extract", url=link_record["url"], status="extract_fail", cooldown_seconds=30)
                    await asyncio.sleep(30)

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
