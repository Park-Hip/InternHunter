# Run Scraper

Current scraper entry points:

```bash
uv run python src/main.py crawl
```

Alternative direct entry point:

```bash
uv run python src/services/crawler/crawl.py
```

## Notes

- The scraper discovers links first, then crawls detail pages.
- It stores raw job rows and audit failures.
