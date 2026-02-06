# Production Scraper Audit: TopCV Crawler (crawl4ai)

**Scope:** `crawl.py`, `src/crawl/crawl_config.py`, `src/database/database.py` (and `src/crawl/crawl_css.py` where it uses config/DB).

---

## Part 1: Gold Standard — Critical Criteria for a Robust MVP Production Scraper

### 1. Reliability & Recovery

| Criterion | Definition |
|-----------|------------|
| **Network resilience** | Retries with backoff on timeouts, connection errors, and transient HTTP errors (e.g. 5xx, 429). Configurable max retries and backoff. |
| **Selector/layout change** | When the site changes DOM/CSS, the scraper fails gracefully (no uncaught exceptions), and failures are detectable (e.g. empty/missing critical fields, or explicit “selector failed” handling). Optionally: fallback selectors or validation steps. |
| **Partial failure & resume** | If the run stops mid-way (crash, kill, deploy), progress is persisted (e.g. “links to do” vs “links done” or DB state). Next run can resume from last state instead of re-crawling everything. |
| **Browser/crawler lifecycle** | Browser is closed on error (context manager or finally), and a single fatal error doesn’t leave the process hanging. |

### 2. Data Integrity

| Criterion | Definition |
|-----------|------------|
| **Deduplication** | Same job (e.g. same canonical URL) is not stored twice. Dedup key (e.g. URL) is normalized (query/fragment stripped) and enforced at write time (DB unique constraint or upsert). |
| **Missing/critical fields** | Critical fields (e.g. title, company, URL) are validated before persisting. Rows with missing critical data are either rejected, logged, or written to a “failed” bucket for later inspection. |
| **Dirty text** | Basic normalization: strip whitespace, collapse newlines where appropriate. No requirement for full NLP; avoid storing raw garbage that breaks downstream (e.g. null bytes, control chars). |
| **Idempotent writes** | Re-running the same URL doesn’t create duplicates and doesn’t corrupt data (INSERT OR IGNORE / REPLACE / proper upsert). |

### 3. Anti-Bot & Safety

| Criterion | Definition |
|-----------|------------|
| **Request rate** | Bounded delay between requests (e.g. min delay and/or jitter). No burst of many requests in a short window. |
| **Block detection** | Response is checked for block/captcha/challenge pages (e.g. “Verify you are human”, “Just a moment”, Cloudflare). On detection: log, optionally save snapshot, and back off or abort instead of parsing garbage. |
| **Production-safe browser** | Headless by default; no “must have a display” in production. Optional override for local debug only. |
| **Secrets** | No API keys or secrets in repo; use env vars or a secret manager. |

### 4. Observability

| Criterion | Definition |
|-----------|------------|
| **Structured logging** | Logs include: run id (or date), phase (e.g. “fetch_links”, “extract_job”), url/link id, outcome (success/fail), and key counts (links found, new, processed, failed). So you can debug from logs without reading code. |
| **Metrics/counts** | At end of run (or periodically): total links, new, processed, failed, duplicates skipped, duration. Either in logs or a simple metrics export. |
| **Failure visibility** | On extract failure: persist enough context to debug (e.g. screenshot, HTML snippet, or saved HTML file) with a stable naming scheme (e.g. by URL hash). |
| **No silent failures** | Errors are logged with message and context; exceptions are not swallowed without a log. |

### 5. Maintainability

| Criterion | Definition |
|-----------|------------|
| **Selectors in one place** | All selectors and crawl config (timeouts, delays, selectors) live in a single module or config file (e.g. `crawl_config.py`), not duplicated across scripts. |
| **Single entry point** | One clear entry (e.g. `crawl.py` or `crawl_css.py`) that runs the full pipeline (fetch links → filter new → extract → persist). No “run this file for phase 1 and that file for phase 2” by default. |
| **Config vs code** | URLs and environment-specific settings (e.g. base URL, headless flag) are config or env, not hardcoded in the middle of logic. |
| **Schema/DB consistency** | DB path and schema are defined in one place; no typos in DB filename; migrations or at least a single `init_db` that is safe to run. |

---

## Part 2: Audit Results (Pass / Partial / Fail)

### 1. Reliability & Recovery

| Criterion | Rating | File(s) | Notes |
|-----------|--------|--------|--------|
| Network resilience | **Fail** | `crawl.py`, `crawl_css.py` | No retries on `arun()`. A single timeout or connection error fails that URL and moves on; no backoff or retry. |
| Selector/layout change | **Partial** | `crawl_css.py` | You check for empty/missing critical fields and save screenshot+HTML on failure (good). No explicit “selector returned nothing” vs “page blocked” distinction; no retry with different strategy. |
| Partial failure & resume | **Fail** | `crawl.py`, `crawl_css.py` | No checkpoint. You append to a daily JSONL and overwrite daily raw_links file. If the process dies at job 50/100, the next run will re-fetch links and re-crawl from the start (or only today’s file). No “remaining links” state. |
| Browser lifecycle | **Pass** | `crawl.py`, `crawl_css.py` | `async with AsyncWebCrawler(...)` is used; browser is closed on exit/exception. |

**Fixes**

**1.1 Retries with backoff (e.g. in `crawl_css.py` or shared util):**

```python
# Add retries for arun() - example using tenacity (you have it in uv.lock)
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((ConnectionError, asyncio.TimeoutError)),
    reraise=True,
)
async def _crawl_with_retry(crawler, url, config):
    return await crawler.arun(url=url, config=config)
```

Then in `extract_single_job`, call `_crawl_with_retry(crawler, url, debug_run_config)` instead of `crawler.arun(...)`. Handle non-retryable cases (e.g. 403, block page) by not retrying.

**1.2 Resume: persist “remaining” links and pass them to Phase 2.**

- After Phase 1, write `raw_links/{date}.jsonl` with all new links.
- In Phase 2, before processing, load `raw_links/{date}.jsonl` and filter out URLs already in `raw_jobs` (you already have `filter_new_links` for “new”, but for resume you need “not yet processed in this run”). Either:
  - maintain a small `state/{date}_processed_urls.txt` (or DB column “processed_at” for today’s run), or
  - derive “remaining” from: links in today’s JSONL minus URLs already in `raw_jobs` with today’s date.
- When starting Phase 2, compute remaining and iterate only over those. Optionally re-write `raw_links/{date}.jsonl` to only remaining so a crash and re-run continues from the same file.

---

### 2. Data Integrity

| Criterion | Rating | File(s) | Notes |
|-----------|--------|--------|--------|
| Deduplication | **Partial** | `database.py`, `crawl_css.py` | You normalize URL with `split('?')[0].split('#')[0]` and use `INSERT OR IGNORE` in `save_raw_job`. Good. But `filter_new_links` is the only place that prevents re-crawling; if someone runs Phase 2 with an old link file, you still don’t duplicate in DB. So DB side: **Pass**. The “Partial” is because crawl phase doesn’t dedupe links by normalized URL before writing to JSONL (e.g. same job with ?ref= could appear twice in raw_links). |
| Missing/critical fields | **Partial** | `crawl_css.py` | You check `title`, `company`, `info` and skip saving + save error assets. Good. Root `crawl.py` does not validate; it only does `data.get('title', 'Unknown')` and can persist junk. |
| Dirty text | **Partial** | `crawl_css.py` | You strip title/company. No generic strip of null bytes or control chars before persist. |
| Idempotent writes | **Pass** | `database.py` | `INSERT OR IGNORE` for raw_jobs; `INSERT OR REPLACE` for clean_jobs. Idempotent. |

**Fixes**

**2.1 Normalize and dedupe links in Phase 1 before writing JSONL (`crawl_css.py`):**

```python
def _normalize_url(url: str) -> str:
    return url.split("?")[0].split("#")[0].strip()

# After getting formatted_links from the crawler:
seen = set()
unique_links = []
for record in formatted_links:
    norm = _normalize_url(record["url"])
    if norm not in seen:
        seen.add(norm)
        unique_links.append(record)
formatted_links = unique_links
# Then filter_new_links(formatted_links)
```

**2.2 Reject rows with missing critical fields in DB layer (`database.py`):**

```python
def save_raw_job(job_data):
    required = ("url", "title", "company")
    for key in required:
        if not job_data.get(key) or not str(job_data.get(key)).strip():
            logger.warning(f"Refusing to save job: missing or empty '{key}'")
            return False
    # ... existing insert logic ...
    return True
```

**2.3 Sanitize dirty text before persist (e.g. in `save_raw_job` or before calling it):**

```python
def _sanitize_text(s: str) -> str:
    if not s:
        return s
    s = s.replace("\x00", "").strip()
    return " ".join(s.split())
```

Use for `title`, `company`, and any other text you store.

---

### 3. Anti-Bot & Safety

| Criterion | Rating | File(s) | Notes |
|-----------|--------|--------|--------|
| Request rate | **Partial** | `crawl.py`, `crawl_css.py` | You have delays (2–4s Phase 1; 3–6s in crawl.py, 10–15s in crawl_css.py between jobs). Good. No upper bound or global rate limiter; a single run is serial so acceptable for MVP. |
| Block detection | **Partial** | `crawl_css.py` only | You check `"Verify you are human"` and `"Just a moment"` in `result.html` and return `None`. Good. Root `crawl.py` has no block detection. |
| Production-safe browser | **Fail** | `crawl_config.py`, `crawl.py` | `headless=False` and `verbose=True` in config and in crawl.py. Production runs must be headless. |
| Secrets | **Pass** | `crawl.py` | Uses `os.getenv("GROQ_API_KEY")`. No keys in repo. |

**Fixes**

**3.1 Headless and verbose from config/env:**

In `crawl_config.py`:

```python
import os

HEADLESS = os.getenv("CRAWL_HEADLESS", "true").lower() in ("1", "true", "yes")
VERBOSE = os.getenv("CRAWL_VERBOSE", "false").lower() in ("1", "true", "yes")

browser_config = BrowserConfig(
    headless=HEADLESS,
    verbose=VERBOSE,
    user_agent_mode="random",
)
```

In root `crawl.py`, if you keep a local `BrowserConfig`, set `headless=True` by default or use the same env.

**3.2 Block detection in root `crawl.py` (if you keep using it):**

After `result = await crawler.arun(...)` in `fetch_job_links` and in `extract_single_job`, add:

```python
if result.success and result.html:
    if "Verify you are human" in result.html or "Just a moment" in result.html:
        logger.warning("Block/captcha detected in response")
        return None  # or retry later
```

---

### 4. Observability

| Criterion | Rating | File(s) | Notes |
|-----------|--------|--------|--------|
| Structured logging | **Partial** | All | You log phase, URL, and some counts. Missing: a stable run id, and consistent fields (e.g. `run_id`, `phase`, `url`, `status`) so logs are grep-able. |
| Metrics/counts | **Partial** | `crawl_css.py` | You log “Filtered: X total -> Y NEW” and “Processing i/total”. No end-of-run summary: total processed, failed, saved, duration. |
| Failure visibility | **Pass** | `crawl_css.py` | Screenshot and HTML saved to `errors/` with URL hash. Good. Root `crawl.py` only logs debug snippets. |
| No silent failures | **Partial** | All | Most errors are logged. In `database.py`, `save_raw_job` and `save_clean_job` catch Exception and log but don’t re-raise; caller doesn’t know the write failed. So “no silent failure” is only partial. |

**Fixes**

**4.1 Run id and structured line (e.g. at start of pipeline):**

```python
import uuid
RUN_ID = str(uuid.uuid4())[:8]
logger.info("run_id=%s phase=start", RUN_ID)
# In each log: logger.info("run_id=%s phase=extract url=%s status=ok", RUN_ID, url)
```

**4.2 End-of-run summary in `crawl_jobs`:**

```python
# At the end of crawl_jobs, after the loop:
logger.info(
    "run_id=%s phase=extract total=%d saved=%d failed=%d duration_sec=%.1f",
    RUN_ID, len(raw_links), saved_count, failed_count, time.monotonic() - start_time,
)
```

Track `saved_count` and `failed_count` in the loop.

**4.3 DB write failure should be visible to caller:**

In `database.py`, re-raise after log so the pipeline can count failures and optionally retry:

```python
except Exception as e:
    logger.error(f"DB Error: {e}")
    raise  # so caller knows write failed
```

If you prefer not to break the whole run, at least return a boolean from `save_raw_job` / `save_clean_job` and let the caller log and increment a failure counter.

---

### 5. Maintainability

| Criterion | Rating | File(s) | Notes |
|-----------|--------|--------|--------|
| Selectors in one place | **Partial** | `crawl_config.py` vs `crawl.py` | `crawl_config.py` has fetch + extract configs. Root `crawl.py` does not use them; it defines its own schema, `run_config`, and `BrowserConfig`. So you have two sources of truth. |
| Single entry point | **Fail** | - | Two entry points: `crawl.py` (LLM extraction, JSONL only) and `src/crawl/crawl_css.py` (CSS + DB). Behavior and output differ. No single “production” entry. |
| Config vs code | **Partial** | `crawl_css.py`, `crawl.py` | `crawl_css.py` uses `load_configs()` for URL. Root `crawl.py` hardcodes `"https://www.topcv.vn/..."`. |
| Schema/DB consistency | **Fail** | `database.py` | `DB_PATH = DATA_DIR / "db" / "  jobs.db"` — typo with two spaces. Creates a different file than likely intended. |

**Fixes**

**5.1 Use one DB path and fix typo in `database.py`:**

```python
DB_PATH = DATA_DIR / "db" / "jobs.db"
```

**5.2 Single entry point:**  
Choose one production path (e.g. CSS + DB in `crawl_css.py`) and make it the only entry. Either:

- Delete or demote root `crawl.py` to a dev-only script, or  
- Make `crawl.py` import and call the same pipeline from `src.crawl.crawl_css` (fetch_job_links → crawl_jobs) and use `crawl_config` + database.  

Then document: “Run `python -m src.crawl.crawl_css` (or `crawl.py`) for full pipeline.”

**5.3 Root `crawl.py` should use config and shared run config:**

- Import `browser_config` and run configs from `src.crawl.crawl_config`.  
- Import search URL from `load_configs()` (or env).  
- Remove duplicate schema and `CrawlerRunConfig` from `crawl.py`.  

---

## Critical Bug: Phase 2 receives list instead of file path

In `src/crawl/crawl_css.py`, `fetch_job_links()` returns **a list** of link dicts when successful, but `crawl_jobs(links_filename)` expects a **file path** and does `os.path.exists(links_filename)` and then `open(links_filename, "r")`. When you run the pipeline and there is no existing file for today, you do:

```python
links_filename = asyncio.run(fetch_job_links())
if links_filename:
    asyncio.run(crawl_jobs(links_filename))
```

So `crawl_jobs` receives a list and will raise when it hits `os.path.exists(links_filename)` (or when opening it). So the “first run of the day” path is broken.

**Fix:** Make the contract consistent.

**Option A – Always pass a file path:**  
In `fetch_job_links`, after writing the JSONL file, return the path (e.g. `links_filename`) instead of `new_links`. You already write the file; just return `str(links_filename)` and use that in `crawl_jobs(links_filename)`.

**Option B – Support both list and path in `crawl_jobs`:**

```python
def _load_links(links_file):
    if isinstance(links_file, (list, tuple)):
        return links_file
    with open(links_file, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
```

Then in `crawl_jobs(links_filename)` use `raw_links = _load_links(links_filename)` and drop the `os.path.exists` check when it’s a list.

Recommendation: **Option A** (return path from `fetch_job_links`) so Phase 2 always reads from disk and you get a natural checkpoint file for the run.

---

## Summary Table

| Area | Pass | Partial | Fail |
|------|------|---------|------|
| Reliability & Recovery | 1 | 1 | 2 |
| Data Integrity | 1 | 3 | 0 |
| Anti-Bot & Safety | 1 | 2 | 1 |
| Observability | 1 | 3 | 0 |
| Maintainability | 0 | 2 | 2 |

**Must-fix before daily production:**  
1. Fix `DB_PATH` typo (`"  jobs.db"` → `"jobs.db"`).  
2. Fix Phase 2 input: `fetch_job_links` should return the written file path (or `crawl_jobs` should accept list/path consistently).  
3. Add retries with backoff for `arun()`.  
4. Use headless (and env) for production browser config.  
5. Single entry point and use `crawl_config` (and database) from that entry.

After that, add resume/checkpoint, structured run id + end-of-run metrics, and DB write failure signaling so you can run daily without crashes and debug easily when the site or environment changes.
