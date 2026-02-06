# Job Finder

MVP pipeline for crawling job listings (TopCV) and processing them.

## Run the crawler (production pipeline)

Single entry point: fetch job links → filter new → extract details → save to DB and JSONL.

```bash
# From project root (with venv activated)
python -m src.crawl.crawl_css
```

- **First run of the day:** Phase 1 fetches links from the search page, writes `src/data/raw_links/YYYY-MM-DD.jsonl`, then Phase 2 crawls each new URL and appends to `src/data/jobs/YYYY-MM-DD.jsonl` and `raw_jobs` in the DB.
- **Re-run / resume:** If you run again the same day, Phase 2 skips URLs already in `raw_jobs` and continues with the rest.

## Environment variables (crawler)

| Variable | Default | Description |
|----------|---------|-------------|
| `CRAWL_HEADLESS` | `true` | Run browser headless. Use `0` or `false` for local debug (visible browser). |
| `CRAWL_VERBOSE` | `false` | Verbose crawl4ai logs. Use `1` or `true` for debugging. |

Example (Windows): `set CRAWL_HEADLESS=0 && set CRAWL_VERBOSE=1 && python -m src.crawl.crawl_css`

## Project layout

- `src/crawl/crawl_css.py` — Crawler entry (Phase 1: links, Phase 2: job details). Uses `crawl_config.py` and `database.py`.
- `src/crawl/crawl_config.py` — Selectors, browser config, run config (headless/verbose from env).
- `src/database/database.py` — SQLite `raw_jobs` / `clean_jobs`, `filter_new_links`, `save_raw_job`.
- `src/data/raw_links/` — Daily JSONL of job URLs.
- `src/data/jobs/` — Daily JSONL of scraped job payloads.
- `src/data/db/jobs.db` — SQLite DB.
- `src/logs/` — Daily pipeline logs.

## Setup

```bash
uv sync   # or: pip install -r requirements.txt
playwright install  # for crawl4ai
```

Search URL and other app config: `src/configs/configs.yaml`.
