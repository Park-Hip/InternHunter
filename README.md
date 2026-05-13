# InternHunter MVP Backend

InternHunter is a TopCV-focused job-finder backend that crawls jobs, stores raw and cleaned job data, generates embeddings, and supports DB search, semantic search, and resume matching.

## Current MVP Backend Capabilities

- TopCV crawl -> `raw_jobs`
- `raw_jobs` -> `clean_jobs`
- `clean_jobs` -> embeddings
- DB-only search
- semantic search
- resume upload -> embedding
- resume matching -> jobs
- minimal local API demo

## Quickstart

### 1. Set up the environment

Make sure PostgreSQL is running and set:

- `DB_URL`
- Gemini API key for embeddings and resume matching

### 2. Run a small ETL slice

```powershell
uv run python src/run_pipeline.py --limit 3 --force-recrawl --skip-llm-validation
```

### 3. Run semantic search smoke

```powershell
uv run python src/scripts/semantic_search_smoke.py
```

Optional query override:

```powershell
uv run python src/scripts/semantic_search_smoke.py --query "python machine learning internship"
```

### 4. Start the API demo

```powershell
uv run uvicorn src.internhunter.api.app:app --reload
```

## API Endpoints

- `GET /health`
- `GET /jobs/search`
- `POST /resume/match`

Examples:

```powershell
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/jobs/search?query=data%20scientist&limit=5"
curl -X POST http://127.0.0.1:8000/resume/match `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"demo-user\",\"resume_text\":\"Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.\",\"limit\":5}"
```

## Documentation

- [MVP backend status](docs/MVP_BACKEND_STATUS.md)
- [MVP demo walkthrough](docs/MVP_DEMO_WALKTHROUGH.md)

## Known Limitations

- TopCV may block crawling with Cloudflare.
- Gemini key/quota is still needed for embeddings and resume matching.
- `match_score` is still coarse in the MVP search results.
- No auth yet.
- No frontend yet.
- `/jobs/search` currently uses DB criteria matching with a recent clean-job fallback, not semantic query embedding yet.

