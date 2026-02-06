import asyncio
import json
import random
import os
import base64
import hashlib
import time
import uuid

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.settings.settings import *
from src.utils.utils import load_configs, parse_info, normalize_url
from src.crawl.crawl_config import *
from src.database.database import JobDatabase

from crawl4ai import AsyncWebCrawler
from crawl4ai.browser_adapter import UndetectedAdapter

# Retry on transient network/IO errors only (do not retry on block/captcha - those are in result)
RETRY_EXCEPTIONS = (ConnectionError, OSError, asyncio.TimeoutError, TimeoutError)

async def _arun_with_retry(crawler, url, config, max_attempts=3):
    """Call crawler.arun with exponential backoff. Raises after max_attempts on network/IO errors."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(RETRY_EXCEPTIONS),
        reraise=True,
    ):
        with attempt:
            return await crawler.arun(url=url, config=config)


logger = logging.getLogger(__name__)

configs = load_configs()

async def fetch_job_links(run_id: str) -> str | None:
    """Fetches job URLs from the search page."""
    logger.info("run_id=%s phase=fetch_links status=start", run_id)

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            url = configs["url"]["ai_engineer"]

            logger.info("run_id=%s phase=fetch_links url=%s", run_id, url)
            await asyncio.sleep(random.uniform(2, 4))

            result = await _arun_with_retry(crawler, url, fetch_link_run_config)

            if result.success:
                if "Verify you are human" in result.html or "Just a moment" in result.html:
                    logger.warning("run_id=%s phase=fetch_links status=block url=%s", run_id, url)
                    return None

                data = json.loads(result.extracted_content)
                logger.info(f"Found {len(data)} jobs.")

                formatted_links = []
                for item in data:
                    raw_url = item.get("url") or ""
                    formatted_links.append({
                        "url": raw_url,
                        "scraped_at": datetime.now().isoformat(),
                        "source": "topcv"
                    })

                # Dedupe by normalized URL (same job with ?ref= etc. only once)
                seen = set()
                unique_links = []
                for record in formatted_links:
                    norm = normalize_url(record["url"])
                    if not norm or norm in seen:
                        continue
                    seen.add(norm)
                    record["url"] = norm  # store canonical URL for DB consistency
                    unique_links.append(record)
                formatted_links = unique_links

                db = JobDatabase()
                new_links = db.filter_new_links(formatted_links)
                logger.info(
                    "run_id=%s phase=fetch_links total=%d new=%d",
                    run_id, len(formatted_links), len(new_links),
                )

                if not new_links:
                    logger.info("run_id=%s phase=fetch_links status=done reason=no_new_jobs", run_id)
                    return None

                links_filename = RAW_LINKS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
                with open(links_filename, "w", encoding="utf-8") as f:
                    for record in new_links:
                        f.write(json.dumps(record, ensure_ascii=False) + "\n")

                logger.info("run_id=%s phase=fetch_links status=ok links_file=%s", run_id, links_filename)
                return str(links_filename)
            else:
                logger.error("run_id=%s phase=fetch_links status=fail error=%s", run_id, result.error_message)
                return None

    except Exception as e:
        logger.error("run_id=%s phase=fetch_links status=error error=%s", run_id, e)
        return None


async def extract_single_job(crawler: AsyncWebCrawler, url: str) -> dict[str, Any] | None:
    delay = random.uniform(10, 15)
    logger.info(f"Sleeping {delay:.1f}s before accessing {url}...")
    await asyncio.sleep(delay)

    debug_run_config = extract_detail_run_config.clone()
    debug_run_config.screenshot = True

    try:
        result = await _arun_with_retry(crawler, url, debug_run_config)

        if not result.success:
            logger.error(f"Network/Crawl Failed {url}: {result.error_message}")
            return None

        data = json.loads(result.extracted_content)

        is_empty = not data or (isinstance(data, list) and not data)
        missing_critical = False

        if isinstance(data, list) and data:
            data = data[0]
        if not isinstance(data, dict):
            logger.warning("extract_fail url=%s failure_reason=non_dict_payload", url)
            return None

            critical_fields = ['title', 'company', 'info']
            for key in critical_fields:
                if not data.get(key):
                    logger.error(f"Missing Critical Field '{key}' in {url}")
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
                "extract_fail url=%s failure_reason=%s is_empty=%s missing_critical=%s",
                url, failure_reason, is_empty, missing_critical,
            )

            safe_id = hashlib.md5(url.encode()).hexdigest()

            os.makedirs("errors", exist_ok=True)

            if result.screenshot:
                img_path = f"errors/error_{safe_id}.png"
                with open(img_path, "wb") as f:
                    f.write(base64.b64decode(result.screenshot))
                logger.info("Saved error screenshot: %s", img_path)

                html_path = f"errors/error_{safe_id}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(result.html)

            return None

        if data.get('raw_info_block'):
            clean_info = parse_info(data.get('info'))
            data.update(clean_info)

        title = data.get('title')
        company = data.get('company')

        if title: title = title.strip()
        if company: company = company.strip()

        logger.info(f"Extracted: {title} @ {company}")

        data['url'] = url
        return data

    except Exception as e:
        logger.error(f"Error extracting {url}: {e}")
        return None


async def crawl_jobs(links_filename: str, run_id: str) -> None:
    db = JobDatabase()
    db.init_db()
    if not links_filename or not os.path.exists(links_filename):
        logger.error("run_id=%s phase=extract status=skip reason=no_links_file", run_id)
        return

    raw_links = []
    with open(links_filename, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                raw_links.append(json.loads(line))

    # Resume: only process links not already in DB (so a re-run continues from where it left off)
    raw_job_count = db.get_raw_job_count()
    remaining_links = db.filter_new_links(raw_links)
    links_from_file = len(raw_links)
    already_in_db = links_from_file - len(remaining_links)

    logger.info(
        "run_id=%s phase=extract status=start db_raw_jobs=%d links_from_file=%d already_in_db=%d remaining=%d",
        run_id, raw_job_count, links_from_file, already_in_db, len(remaining_links),
    )

    if not remaining_links:
        logger.info("run_id=%s phase=extract status=done reason=no_remaining_links", run_id)
        return

    output_filename = JOBS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"
    start_time = time.monotonic()
    saved_count = 0
    failed_count = 0

    adapter = UndetectedAdapter()
    async with AsyncWebCrawler(config=browser_config, browser_adapter=adapter) as crawler:
        with open(output_filename, "a", encoding="utf-8") as f_out:
            for i, link_record in enumerate(remaining_links):
                logger.info(
                    "run_id=%s phase=extract progress=%d/%d url=%s",
                    run_id, i + 1, len(remaining_links), link_record["url"],
                )

                job_data = await extract_single_job(crawler, link_record["url"])

                if job_data:
                    if db.save_raw_job(job_data):
                        saved_count += 1
                        f_out.write(json.dumps(job_data, ensure_ascii=False) + "\n")
                        f_out.flush()
                    else:
                        failed_count += 1
                        logger.warning("run_id=%s phase=extract url=%s status=db_fail", run_id, link_record["url"])
                else:
                    failed_count += 1
                    logger.info("run_id=%s phase=extract url=%s status=extract_fail cooling 30s", run_id, link_record["url"])
                    await asyncio.sleep(30)

    duration_sec = time.monotonic() - start_time
    logger.info(
        "run_id=%s phase=extract status=done total=%d saved=%d failed=%d duration_sec=%.1f output=%s",
        run_id, len(remaining_links), saved_count, failed_count, duration_sec, output_filename,
    )


if __name__ == "__main__":
    log_filename = f"{LOGS_DIR}/pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )

    run_id = str(uuid.uuid4())[:8]
    logger.info("run_id=%s pipeline=start", run_id)

    current_file = RAW_LINKS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.jsonl"

    if os.path.exists(current_file):
        asyncio.run(crawl_jobs(str(current_file), run_id))
    else:
        links_filename = asyncio.run(fetch_job_links(run_id))
        if links_filename:
            asyncio.run(crawl_jobs(links_filename, run_id))

# if __name__ == "__main__":
#     links_filename = Path("test.jsonl")
#     asyncio.run(crawl_jobs(links_filename))

