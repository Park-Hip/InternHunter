import asyncio
import json
import random
import os
import base64
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.core.utils import normalize_url
from src.core.models.fetch_result import FetchOutcome, FetchStatus
from src.core.models.extraction_result import ExtractionResult
from src.infrastructure.db.repositories.etl import ETLRepository
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


def _extract_raw_markdown(result) -> str | None:
    """Compatibility helper for crawl4ai markdown result shapes."""
    markdown_result = getattr(result, "markdown", None)
    if markdown_result is None:
        markdown_result = getattr(result, "markdown_v2", None)

    if markdown_result is None:
        return None

    if isinstance(markdown_result, str):
        return markdown_result

    return getattr(markdown_result, "raw_markdown", None)


class Crawler:
    def __init__(self):
        self.search_urls = settings.search_urls
        self.max_pages = settings.crawler.max_pages

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

    async def _fetch_single_page(self, crawler, url: str) -> tuple[list[dict], FetchStatus | None]:
        """Fetch links from a single search result page.
        
        Returns:
            (links, error_status) — links found on this page, and an error status if something went wrong.
            If error_status is not None, the caller should stop pagination.
        """
        await asyncio.sleep(random.uniform(2, 4))

        try:
            result = await self._arun_with_retry(crawler, url, fetch_link_run_config)
        except Exception as e:
            logger.error("Network error fetching page", phase="fetch_links", url=url, error=str(e))
            return [], FetchStatus.NETWORK_FAIL

        if not result.success:
            logger.error("Crawl failed for page", phase="fetch_links", url=url, error=result.error_message)
            return [], FetchStatus.NETWORK_FAIL

        # Check for bot blocking
        if "Verify you are human" in (result.html or "") or "Just a moment" in (result.html or ""):
            logger.warning("Blocked by captcha/verification", phase="fetch_links", status="block", url=url)
            return [], FetchStatus.BLOCKED

        # Parse extracted content with guard
        try:
            data = json.loads(result.extracted_content or "[]")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse extracted content", phase="fetch_links",
                         error=str(e), content_preview=str(result.extracted_content)[:200])
            return [], FetchStatus.PARSE_ERROR

        if not isinstance(data, list) or not data:
            logger.info("No links found on page", phase="fetch_links", url=url)
            return [], None  # Empty page = end of pagination, not an error

        # Normalize URLs
        page_links = []
        for item in data:
            raw_url = item.get("url") or ""
            normalized = normalize_url(raw_url)
            if normalized:
                page_links.append({
                    "url": normalized,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "source": "topcv"
                })

        return page_links, None

    async def fetch_job_links(self, run_id: str, limit: int | None = None, force_recrawl: bool = False) -> FetchOutcome:
        """Fetches job URLs from all configured search pages with pagination.

        Iterates through all search URLs (DS_URL, AIE_URL, etc.) and paginates
        each one up to max_pages. Returns a typed FetchOutcome so the caller
        can distinguish between blocked/error/empty/success states.
        """
        bind_context(run_id=run_id)
        logger.info("Fetch links phase starting", phase="fetch_links", status="start",
                    search_urls=len(self.search_urls), max_pages=self.max_pages)
        if force_recrawl:
            logger.warning("Force-recrawl mode enabled for link discovery", phase="fetch_links", run_id=run_id)

        all_links = []
        total_pages_scraped = 0
        last_error_status = None
        reached_limit = False

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                for base_url in self.search_urls:
                    logger.info("Scraping search URL", phase="fetch_links", base_url=base_url)

                    for page in range(1, self.max_pages + 1):
                        # Build paginated URL
                        page_url = f"{base_url}&page={page}" if page > 1 else base_url
                        logger.info("Fetching page", phase="fetch_links", url=page_url, page=page)

                        page_links, error_status = await self._fetch_single_page(crawler, page_url)

                        if error_status is not None:
                            last_error_status = error_status
                            logger.warning("Stopping pagination for URL", phase="fetch_links",
                                           base_url=base_url, reason=error_status.value, page=page)
                            break  # Stop paginating this URL, move to next

                        if not page_links:
                            logger.info("No more results, stopping pagination", phase="fetch_links",
                                        base_url=base_url, page=page)
                            break  # Empty page = no more results

                        all_links.extend(page_links)
                        total_pages_scraped += 1
                        logger.info("Page scraped", phase="fetch_links", page=page,
                                    links_on_page=len(page_links), total_so_far=len(all_links))

                        if limit is not None and len(all_links) >= limit:
                            reached_limit = True
                            logger.info(
                                "Fetch links limit reached",
                                phase="fetch_links",
                                limit=limit,
                                total_so_far=len(all_links),
                            )
                            break

                    if reached_limit:
                        break

            # Dedup against database unless the caller explicitly requested a dev-only recrawl.
            if not all_links:
                status = last_error_status or FetchStatus.NO_NEW
                logger.info("Fetch links completed with no links", phase="fetch_links",
                            status=status.value, pages_scraped=total_pages_scraped)
                return FetchOutcome(status=status, pages_scraped=total_pages_scraped)

            if force_recrawl:
                new_links = all_links
            else:
                repo = ETLRepository()
                new_links = repo.filter_new_links(all_links)

            logger.info("Links filtered", phase="fetch_links",
                        total_scraped=len(all_links), new=len(new_links),
                        pages_scraped=total_pages_scraped)

            if not new_links:
                return FetchOutcome(
                    status=FetchStatus.NO_NEW,
                    total_scraped=len(all_links),
                    pages_scraped=total_pages_scraped
                )

            if limit is not None and len(new_links) > limit:
                new_links = new_links[:limit]

            return FetchOutcome(
                status=FetchStatus.SUCCESS,
                links=new_links,
                total_scraped=len(all_links),
                pages_scraped=total_pages_scraped
            )

        except Exception as e:
            logger.error("Fetch links exception", phase="fetch_links", status="error",
                         error=str(e), exc_info=True)
            return FetchOutcome(status=FetchStatus.NETWORK_FAIL, error=str(e))

        finally:
            clear_context()


    async def extract_single_job(self, crawler: AsyncWebCrawler, url: str) -> ExtractionResult | None:
        """Extract a single job page. Returns typed ExtractionResult or None on total failure."""
        delay = random.uniform(settings.crawler.extract_delay_min, settings.crawler.extract_delay_max)
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
            css_fields = ['title', 'company', 'salary', 'location', 'experience', 'info']
            is_valid_css = (
                isinstance(data, dict) and 
                data.get('title') and 
                data.get('info') and 
                len(str(data.get('info'))) > 200
            )
            
            if is_valid_css:
                found = [k for k in css_fields if data.get(k)]
                missing = [k for k in css_fields if not data.get(k)]
                logger.info("CSS extraction successful", url=url,
                            fields_found=",".join(found), fields_missing=",".join(missing))
                return ExtractionResult(
                    url=url,
                    title=data.get('title', '').strip(),
                    company=data.get('company', '').strip(),
                    location=data.get('location', '').strip(),
                    full_json_dump=data,
                    extraction_method="css",
                    status="pending"
                )
            else:
                # 2. Fallback to RAW Markdown
                logger.warning("CSS extraction failed/poor quality, using RAW fallback", url=url)
                
                html = (result.html or "")
                is_blocked = "Verify you are human" in html or "Just a moment" in html
                blocked_reason = None
                if is_blocked:
                    blocked_reason = "blocked_or_empty_content"
                elif not data:
                    blocked_reason = "empty_or_unparseable_css_content"
                
                return ExtractionResult(
                    url=url,
                    title="Unknown (RAW)",
                    company="Unknown (RAW)",
                    location="Unknown",
                    raw_markdown=_extract_raw_markdown(result),
                    extraction_method="raw",
                    status="blocked" if is_blocked else "pending",
                    screenshot=result.screenshot,
                    html=result.html,
                    full_json_dump={
                        "error": "CSS extraction failed",
                        "is_blocked": is_blocked,
                        "blocked_reason": blocked_reason,
                    }
                )

        except Exception as e:
            logger.error("Extraction error", url=url, error=str(e), exc_info=True)
            return None

    def _save_screenshot(self, screenshot_b64: str | None, url: str) -> str | None:
        """Save a base64 screenshot to disk for debugging blocked pages."""
        if not screenshot_b64:
            return None
        try:
            safe_id = hashlib.md5(url.encode()).hexdigest()
            errors_dir = settings.BASE_DIR / "errors"
            os.makedirs(errors_dir, exist_ok=True)
            img_path = str(errors_dir / f"error_{safe_id}_{int(time.time())}.png")
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(screenshot_b64))
            return img_path
        except Exception as e:
            logger.warning("Failed to save screenshot", error=str(e))
            return None

    async def crawl_jobs(self, new_links, run_id: str, force_recrawl: bool = False) -> tuple[int, int]:
        """Crawl new_links fetched by fetch_job_links().
        
        Returns:
            (saved_count, failed_count) so the flow can record extraction telemetry.
        """
        bind_context(run_id=run_id)
        if not new_links:
            logger.error("Extract phase skipped", phase="extract", status="skip", reason="no_links")
            return 0, 0
        if force_recrawl:
            logger.warning("Force-recrawl mode enabled for job crawling", phase="extract", run_id=run_id)

        repo = ETLRepository()
        raw_jobs_count = repo.get_raw_jobs_count()
        # Defensive re-check: links may have been saved by a concurrent pipeline run
        # between fetch_job_links() and crawl_jobs(). Safe to keep unless force-recrawl was explicitly requested.
        if force_recrawl:
            remaining_links = new_links
        else:
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
            return 0, 0

        start_time = time.monotonic()
        saved_count = 0
        failed_count = 0

        adapter = UndetectedAdapter()
        async with AsyncWebCrawler(config=browser_config, browser_adapter=adapter) as crawler:
            for i, link_record in enumerate(remaining_links):
                url = link_record["url"]
                logger.info(
                    "Processing job",
                    phase="extract",
                    progress=f"{i + 1}/{len(remaining_links)}",
                    url=url
                )

                extraction = await self.extract_single_job(crawler, url)

                if extraction:
                    if repo.save_raw_job(extraction.to_save_dict()):
                        saved_count += 1
                        
                        # Handle immediate audit if blocked
                        if extraction.status == "blocked":
                            repo.save_to_audit({
                                "url": url,
                                "error_type": "BOT_DETECTED",
                                "error_message": "Blocked by captcha/verification",
                                "screenshot_path": self._save_screenshot(extraction.screenshot, url),
                                "html_content": extraction.html
                            })
                    else:
                        failed_count += 1
                        logger.warning("Database save failed", phase="extract", url=url, status="db_fail")

                else:
                    failed_count += 1
                    logger.info("Extraction failed completely", phase="extract", url=url, status="extract_fail")
                    repo.save_to_audit({
                        "url": url,
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
        return saved_count, failed_count


async def run_crawler_pipeline(run_id: str):
    """Main pipeline entry point."""
    crawler = Crawler()
    outcome = await crawler.fetch_job_links(run_id)
    if outcome.is_success and outcome.links:
        await crawler.crawl_jobs(outcome.links, run_id)


if __name__ == "__main__":

    configure_logging()
    
    run_id = str(uuid.uuid4())[:8]
    logger.info("Crawler pipeline starting", run_id=run_id)

    asyncio.run(run_crawler_pipeline(run_id))
