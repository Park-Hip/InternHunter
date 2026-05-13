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

## Required Environment

Minimum required environment:

1. `DB_URL`
2. Gemini API key for embeddings

Still needed in some paths:

1. Groq/Gemini for LLM validation and extraction when LLM validation is enabled
2. Groq/Gemini for chat-tool paths that use LLM routing

Notes:

- `--skip-llm-validation` avoids Gemini validation quota during local ETL iteration.
- Embeddings still use the canonical Gemini-backed embedder.

## Known Limitations

The MVP backend works, but the following limitations are still known:

1. TopCV Cloudflare blocking still happens on live crawls.
2. CSS extraction often falls back to raw fallback.
3. `match_score` in semantic search is currently coarse / placeholder-like.
4. `--force-recrawl` is dev-only and should not be treated as a production mode.
5. `--skip-llm-validation` is dev-only and should not be treated as a production mode.
6. There is no UI yet.
7. There is no polished API demo yet.

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

## Next Recommended Milestone

The next best milestone is to build a simple API or minimal UI demo around:

1. search
2. resume matching

That would make the current backend capabilities easier to validate and share without needing the full agent/chat experience.
