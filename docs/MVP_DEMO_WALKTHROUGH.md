# MVP Demo Walkthrough

This is the shortest reliable local walkthrough for the current InternHunter MVP backend.

## 1. Prerequisites

Before starting, make sure:

1. PostgreSQL is running.
2. `DB_URL` is set.
3. A Gemini API key is available for embeddings and resume matching.

## 2. Run the ETL Slice

Run a small dev-safe ETL slice:

```powershell
uv run python src/run_pipeline.py --limit 3 --force-recrawl --skip-llm-validation
```

## 3. Verify Data

Check the main pipeline tables.

### raw_jobs

```sql
SELECT id, url, title, status, extraction_method, retry_count, created_at
FROM raw_jobs
ORDER BY id DESC
LIMIT 10;
```

### clean_jobs

```sql
SELECT id, raw_job_id, standardized_title, job_level, is_internship, embedding IS NOT NULL AS has_embedding, created_at
FROM clean_jobs
ORDER BY id DESC
LIMIT 10;
```

### audit_jobs

```sql
SELECT id, url, error_type, error_message, created_at
FROM audit_jobs
ORDER BY id DESC
LIMIT 10;
```

## 4. Run Semantic Search Smoke

Run the semantic search smoke script:

```powershell
uv run python src/scripts/semantic_search_smoke.py
```

Optional query override:

```powershell
uv run python src/scripts/semantic_search_smoke.py --query "python machine learning internship"
```

## 5. Start the API

Start the local demo API:

```powershell
uv run uvicorn src.internhunter.api.app:app --reload
```

## 6. Test the Endpoints

### Health

```powershell
curl http://127.0.0.1:8000/health
```

### Jobs Search

```powershell
curl "http://127.0.0.1:8000/jobs/search?query=data%20scientist&limit=5"
```

### Resume Match

```powershell
curl -X POST http://127.0.0.1:8000/resume/match `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"demo-user\",\"resume_text\":\"Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.\",\"limit\":5}"
```

## 7. Expected Successful Outputs

If everything is working, you should see:

1. ETL logs that show the crawl, raw save, and processing stages completing or skipping cleanly.
2. `raw_jobs` rows populated.
3. `clean_jobs` rows populated, with at least some `embedding IS NOT NULL`.
4. Semantic search printing job results with title, company, cities, URL, and match score.
5. `/health` returning:
   - `{"status":"ok","db":"ok","search":"ready"}`
6. `/jobs/search` returning a list of jobs.
7. `/resume/match` returning a list of matched jobs.

## 8. Common Failures

The most likely failure points are:

1. TopCV Cloudflare blocks the crawl.
2. Gemini quota blocks validation, embedding, or resume upload.
3. No `clean_jobs` rows exist yet.
4. No embeddings exist yet in `clean_jobs`.
5. `match_score` looks coarse because semantic ranking is still a minimal MVP implementation.

## 9. What “MVP Success” Means

The MVP is successful if all of these are true:

1. The ETL slice completes.
2. Raw jobs are saved.
3. Clean jobs are created.
4. Embeddings are present.
5. Semantic search returns results.
6. The API demo starts.
7. `/health`, `/jobs/search`, and `/resume/match` all return useful responses locally.
