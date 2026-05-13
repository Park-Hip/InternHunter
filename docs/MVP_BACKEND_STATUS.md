# MVP Backend Status

This document captures the current working backend MVP path, the local smoke commands, and the main limitations that still need product and engineering polish.

## Working Paths

The following backend slices are working end to end in the local environment:

1. TopCV crawl -> `raw_jobs`
2. `raw_jobs` -> `clean_jobs`
3. `clean_jobs` -> embeddings
4. DB-only search
5. Semantic search
6. Resume upload -> embedding
7. Resume matching -> jobs
8. API demo

## Supported Local Commands

### Local ETL slice

Runs a small, dev-safe slice with crawl recrawl enabled and LLM validation disabled:

```powershell
uv run python src/run_pipeline.py --limit 3 --force-recrawl --skip-llm-validation
```

### Semantic search smoke

Runs a real query embedding against the current `clean_jobs.embedding` data:

```powershell
uv run python src/scripts/semantic_search_smoke.py
```

Optional query override:

```powershell
uv run python src/scripts/semantic_search_smoke.py --query "python machine learning internship"
```

### Resume matching smoke

The simplest current smoke path uses the chat tool layer directly:

```powershell
uv run python -c "from src.services.chat.tools import execute_upload_resume, execute_match_resume; user_id='smoke-user'; resume='Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.'; print(execute_upload_resume(user_id, resume)); print(execute_match_resume(user_id, limit=5))"
```

### API demo

Run the local demo API:

```powershell
uv run uvicorn src.internhunter.api.app:app --reload
```

Available endpoints:

1. `GET /health`
2. `GET /jobs/search` (`mode=criteria` by default, `mode=semantic` when Gemini embedding is configured)
3. `POST /resume/match`

## Required Environment

Minimum required environment:

1. `DB_URL`
2. Gemini API key for embeddings

Still needed in some paths:

1. Groq/Gemini for LLM validation and extraction when LLM validation is enabled
2. Groq/Gemini for chat-tool paths that use LLM routing
3. Gemini API key for the `/resume/match` demo endpoint

Notes:

- `--skip-llm-validation` avoids Gemini validation quota during local ETL iteration.
- Embeddings still use the canonical Gemini-backed embedder.

## Known Limitations

The MVP backend works, but the following limitations are still known:

1. TopCV Cloudflare blocking still happens on live crawls.
2. CSS extraction often falls back to raw fallback.
3. `match_score` is meaningful in semantic search, but criteria mode still uses exact/fallback behavior.
4. `--force-recrawl` is dev-only and should not be treated as a production mode.
5. `--skip-llm-validation` is dev-only and should not be treated as a production mode.
6. There is no UI yet.
7. There is no polished API demo yet.
8. `/jobs/search` supports both criteria and semantic modes; semantic mode depends on the Gemini embedding key/quota.
9. `/resume/match` needs a Gemini embedding key.
10. There is no auth.

## Verification Commands

### Unit tests

```powershell
uv run pytest tests/unit -q
```

### ETL smoke

```powershell
uv run python src/run_pipeline.py --limit 3 --force-recrawl --skip-llm-validation
```

### Search smoke

```powershell
uv run python src/scripts/semantic_search_smoke.py
```

### Resume smoke

```powershell
uv run python -c "from src.services.chat.tools import execute_upload_resume, execute_match_resume; user_id='smoke-user'; resume='Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.'; print(execute_upload_resume(user_id, resume)); print(execute_match_resume(user_id, limit=5))"
```

### API demo smoke

```powershell
uv run uvicorn src.internhunter.api.app:app --reload
```

## Next Recommended Milestone

The next best milestone is to build a simple API or minimal UI demo around:

1. search
2. resume matching

That would make the current backend capabilities easier to validate and share without needing the full agent/chat experience.

## API Demo

The minimal local demo API is now available with these endpoints:

### `GET /health`

```powershell
curl http://127.0.0.1:8000/health
```

### `GET /jobs/search`

```powershell
curl "http://127.0.0.1:8000/jobs/search?query=data%20scientist&limit=5"
```

Semantic mode:

```powershell
curl "http://127.0.0.1:8000/jobs/search?query=python%20machine%20learning&limit=5&mode=semantic"
```

### `POST /resume/match`

```powershell
curl -X POST http://127.0.0.1:8000/resume/match `
  -H "Content-Type: application/json" `
  -d "{\"user_id\":\"demo-user\",\"resume_text\":\"Python data scientist with machine learning, SQL, NLP, statistics, FastAPI, and data visualization experience.\",\"limit\":5}"
```

### Current MVP Status

The backend MVP is now working across:

1. ETL
2. DB search
3. semantic search
4. resume matching
5. API demo

### API Demo Limitations

1. No auth.
2. No frontend.
3. `/jobs/search` defaults to criteria mode, but `mode=semantic` is available when Gemini is configured.
4. Semantic `/jobs/search` depends on Gemini key/quota.
5. `/resume/match` needs a Gemini embedding key.
6. TopCV may block crawling.
7. `match_score` is meaningful in semantic mode, but criteria mode still uses exact/fallback behavior.
