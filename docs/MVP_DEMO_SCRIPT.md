# MVP Demo Script

Use this as the talking track for a live backend MVP presentation.

## 1. Opening Explanation

**What InternHunter is**
- InternHunter is a job-finding backend focused on TopCV job data.
- It crawls jobs, normalizes them, generates embeddings, and supports search and resume matching.

**What problem it solves**
- It reduces the manual work of finding relevant jobs by turning raw job pages into searchable, matchable data.
- It also supports resume-based matching so candidates can quickly see jobs that fit their profile.

**Why the backend MVP matters**
- The backend MVP proves the core pipeline works end to end:
  crawl -> store -> process -> embed -> search -> match -> serve via API.
- That gives us a solid foundation before adding a polished UI or broader product features.

## 2. Architecture Overview

Say this simply:

> TopCV pages are crawled into raw job snapshots, those raw jobs are cleaned into structured jobs, structured jobs get embeddings, and then we can search jobs, match resumes, and expose it through a small API demo.

Flow:

TopCV crawl
-> raw_jobs
-> clean_jobs
-> embeddings
-> search
-> resume matching
-> API demo

## 3. Demo Steps

### Step 1: Run the ETL slice

Command:

```powershell
uv run python src/run_pipeline.py --limit 3 --force-recrawl --skip-llm-validation
```

What to say:
- “I’m running a small local ETL slice so we can see the full pipeline without a large crawl.”
- “This fetches a few TopCV jobs, stores raw snapshots, and processes only a tiny batch.”

What the output proves:
- Crawling works.
- Raw job persistence works.
- Clean job processing works.
- The pipeline can run in a local dev-safe mode.

Success looks like:
- Raw jobs are saved.
- Clean jobs are created.
- The run completes without broad failures.

### Step 2: Inspect the database

Use these SQL queries:

`raw_jobs`

```sql
SELECT id, url, title, status, extraction_method, retry_count, created_at
FROM raw_jobs
ORDER BY id DESC
LIMIT 10;
```

`clean_jobs`

```sql
SELECT id, raw_job_id, standardized_title, job_level, is_internship, embedding IS NOT NULL AS has_embedding, created_at
FROM clean_jobs
ORDER BY id DESC
LIMIT 10;
```

`audit_jobs`

```sql
SELECT id, url, error_type, error_message, created_at
FROM audit_jobs
ORDER BY id DESC
LIMIT 10;
```

What to say:
- “Here I’m checking the pipeline artifacts directly in the database.”
- “Raw jobs show the crawl result, clean jobs show structured outputs, and audit jobs show failures or blocked pages.”

What the output proves:
- The ETL really wrote data.
- Some clean jobs have embeddings.
- Any failures are visible and explainable.

Success looks like:
- `raw_jobs` has new rows.
- `clean_jobs` has rows and at least some embeddings.
- `audit_jobs` is either empty or only contains expected failures like blocked pages.

### Step 3: Run semantic search smoke

Command:

```powershell
uv run python src/scripts/semantic_search_smoke.py
```

Optional:

```powershell
uv run python src/scripts/semantic_search_smoke.py --query "python machine learning internship"
```

What to say:
- “Now I’m generating a real query embedding and searching the current clean job set semantically.”

What the output proves:
- Embeddings exist.
- Semantic search works end to end.
- The backend can surface relevant jobs from a natural language query.

Success looks like:
- The script prints a short ranked list of jobs with title, company, cities, URL, and match score.

### Step 4: Start the API

Command:

```powershell
uv run uvicorn src.internhunter.api.app:app --reload
```

What to say:
- “This exposes the MVP backend through a minimal FastAPI demo.”
- “The API is intentionally small so it stays easy to understand and demo.”

### Step 5: Call the endpoints

`GET /health`

```powershell
curl http://127.0.0.1:8000/health
```

Say:
- “This is a lightweight health check.”

Success looks like:
- `{"status":"ok","db":"ok","search":"ready"}`

`GET /jobs/search`

```powershell
curl "http://127.0.0.1:8000/jobs/search?query=data%20scientist&limit=5"
```

Say:
- “This is the simplest search endpoint in the demo.”
- “It uses the current clean job data and returns relevant jobs.”

Success looks like:
- A list of jobs with titles, companies, cities, URLs, and salary ranges.

`POST /resume/match`

```powershell
curl -X POST http://127.0.0.1:8000/resume/match `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"demo-user\",\"resume_text\":\"Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.\",\"limit\":5}"
```

Say:
- “This is the resume matching demo.”
- “It embeds the resume text and returns the most relevant jobs.”

Success looks like:
- A list of matched jobs with job titles, companies, cities, URLs, and match scores.

## 4. Honest Limitations to Mention

Be direct about the current rough edges:

- TopCV can still block crawling with Cloudflare.
- Gemini key/quota is still needed for embeddings and resume matching.
- `match_score` is still coarse in the current MVP.
- There is no auth yet.
- There is no frontend yet.
- `--force-recrawl` is dev-only.
- `--skip-llm-validation` is dev-only.

## 5. Strong Closing Summary

Close with something like this:

> The backend MVP is working end to end: we can crawl TopCV jobs, store and process them, generate embeddings, search semantically, match resumes, and expose it through a minimal API. The next milestones are to make `/jobs/search` more semantic, build a tiny UI, improve ranking, and harden the system for production use.

## 6. Suggested Next Milestones

1. Make `/jobs/search` semantic by default.
2. Build a tiny UI on top of the API.
3. Improve ranking and scoring.
4. Harden the pipeline for production reliability.
