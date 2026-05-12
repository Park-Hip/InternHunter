# Current Behavior

This file describes what the code does today, not what it should do later.

## What Works Today

- TopCV job links are discovered from the configured search URLs in `src/config/settings.py`.
- The crawler paginates search results and normalizes job URLs before saving.
- Detail extraction uses a CSS-first path and falls back to raw markdown when CSS extraction looks weak.
- Raw jobs are stored in PostgreSQL as staging rows.
- Validation runs before LLM parsing.
- LLM parsing uses Gemini first and Groq as fallback.
- Embeddings are generated at 768 dimensions.
- Structured jobs are stored in `clean_jobs`.
- Failures are recorded in `audit_jobs`.
- Pipeline runs are summarized in `pipeline_runs`.
- Chat history and user resume data are stored in the chat tables.

## Known Commands

- `uv run python src/run_pipeline.py --limit 10`
- `uv run python src/main.py crawl`
- `uv run python src/main.py process --limit 10`
- `uv run python src/main.py init-db`
- `uv run python src/main.py serve --host 0.0.0.0 --port 8000`
- `uv run python src/scripts/upgrade_db.py`
- `docker-compose up -d`

## Known Modules and Files

- `src/config/settings.py`
- `src/config/settings.yaml`
- `src/config/prompts.yaml`
- `src/flows/ingestion_flow.py`
- `src/run_pipeline.py`
- `src/main.py`
- `src/services/crawler/crawl.py`
- `src/services/crawler/crawl_config.py`
- `src/services/job_processor/job_processor.py`
- `src/services/job_processor/validator.py`
- `src/services/job_processor/embedder.py`
- `src/infrastructure/db/models.py`
- `src/infrastructure/db/session.py`
- `src/infrastructure/db/repositories/etl.py`
- `src/infrastructure/db/repositories/search.py`
- `src/infrastructure/db/repositories/chat.py`
- `src/infrastructure/llm/router.py`
- `src/infrastructure/llm/providers.py`
- `src/infrastructure/api/routes/chat_routes.py`
- `src/services/chat/agent.py`
- `src/services/chat/tools.py`
- `src/services/chat/memory.py`
- `tests/unit/test_job_processor.py`
- `tests/unit/test_etl_repository.py`
- `tests/integration/test_ingestion_flow.py`

## Known Problems

- TODO: verify from codebase, but `src/infrastructure/api/routes/chat_routes.py` imports `src.infrastructure.db.repository.MemoryRepository`, while the repo contains `src/infrastructure/db/repositories/`.
- TODO: verify from codebase, but `src/services/chat/memory.py` has the same `MemoryRepository` import mismatch.
- TODO: verify from codebase, but there are two orchestration paths: `src/flows/ingestion_flow.py` and `src/infrastructure/prefect/flows.py`.
- TODO: verify from codebase, but `Dockerfile` points to `src.scripts.deployment`, which is not present in the repo.
- Search and resume matching exist mainly as repository and chat-tool code, not as dedicated API endpoints yet.
- Test coverage is present, but it is still narrow and heavily mocked.

## Must Not Break

- URL deduplication before saving raw jobs.
- CSS-first extraction with raw fallback.
- Blocked-page audit handling and screenshot capture.
- Validation before LLM parsing.
- Gemini -> Groq fallback behavior.
- 768-dimension embedding generation.
- `raw_jobs.status` transitions to `completed` or `failed`.
- `pipeline_runs` telemetry writes.
