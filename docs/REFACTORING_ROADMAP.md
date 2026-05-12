# Refactoring Roadmap

This roadmap answers one question: what should we refactor first, and in what order?

## Recommended First Step

Start with the shared foundation, not the business logic.

The first safe module to stabilize is:

1. `src/internhunter/config`
2. `src/internhunter/common`

These modules unblock every other layer because they define how configuration and logging behave everywhere else.

## Phase-by-Phase Checklist

### Phase 1: Foundation

Do these in order:
1. Keep `src/config/settings.py` working as the legacy source of truth for now.
2. Keep `src/infrastructure/logging/config.py` working as the legacy source of truth for now.
3. Make `src/internhunter/config/settings.py` and `src/internhunter/common/logging.py` the new home for the shared foundation.
4. Add temporary compatibility imports where needed so old imports still resolve.
5. Add a minimal test that imports the new foundation modules.
6. Verify the current commands still start:
   - `uv run python src/main.py init-db`
   - `uv run python src/main.py crawl`
   - `uv run python src/run_pipeline.py --limit 10`

Exact file order:
- `src/internhunter/config/settings.py`
- `src/internhunter/common/logging.py`
- `src/internhunter/config/__init__.py`
- `src/internhunter/common/__init__.py`
- compatibility shims in legacy paths only if required

### Phase 2: Storage

Do these in order:
1. Move ORM definitions into the new storage namespace.
2. Move the database session factory next.
3. Move ETL repository logic after the ORM/session layer is stable.
4. Keep repository method names and return shapes unchanged.
5. Add repository tests before changing any call sites.

Exact file order:
- `src/infrastructure/db/models.py`
- `src/infrastructure/db/session.py`
- `src/infrastructure/db/repositories/etl.py`
- `src/infrastructure/db/repositories/search.py`
- `src/infrastructure/db/repositories/chat.py`

### Phase 3: Orchestration

Do these in order:
1. Decide whether `src/flows/ingestion_flow.py` or `src/infrastructure/prefect/flows.py` is canonical.
2. Keep one flow as the entry point and mark the other as legacy.
3. Move CLI wrappers only after the flow boundary is settled.
4. Preserve existing command names.

Exact file order:
- `src/flows/ingestion_flow.py`
- `src/infrastructure/prefect/tasks.py`
- `src/infrastructure/prefect/flows.py`
- `src/run_pipeline.py`
- `src/main.py`

### Phase 4: Ingestion

Do these in order:
1. Move crawler config first.
2. Move crawler implementation second.
3. Preserve link discovery and extraction behavior exactly.
4. Add fixture-based scraper tests before any extraction logic change.

Exact file order:
- `src/services/crawler/crawl_config.py`
- `src/services/crawler/crawl.py`

### Phase 5: Extraction and Embeddings

Do these in order:
1. Move validation first.
2. Move job processing next.
3. Move embedding generation last.
4. Do not change validation criteria, fallback rules, or embedding dimensionality in this phase.

Exact file order:
- `src/services/job_processor/validator.py`
- `src/services/job_processor/job_processor.py`
- `src/services/job_processor/embedder.py`
- `src/infrastructure/llm/base.py`
- `src/infrastructure/llm/providers.py`
- `src/infrastructure/llm/router.py`

### Phase 6: Search and Resume

Do these in order:
1. Move structured search repository code.
2. Move similarity search code.
3. Move chat-tool resume matching after search is stable.
4. Keep the current chat tool contract stable until tests cover the new path.

Exact file order:
- `src/infrastructure/db/repositories/search.py`
- `src/services/chat/tools.py`
- `src/services/chat/agent.py`
- `src/services/chat/memory.py`

### Phase 7: API

Do these in order:
1. Move route handlers only after their service dependencies are stable.
2. Fix stale imports while moving, but do not redesign the API yet.
3. Add endpoint tests after the route move.

Exact file order:
- `src/infrastructure/api/routes/chat_routes.py`

## Why Start Here

- configuration is read by crawler, processor, storage, orchestration, and API code
- logging is used across every runtime path
- these are move-only refactors with low behavior risk
- they make the later migration of services much safer

## Safe Refactor Order

### Phase 1: Foundation

Move or wrap:
- configuration loading
- prompt loading
- logging setup
- shared utilities and shared types

Target code:
- `src/config/settings.py`
- `src/infrastructure/logging/*`
- `src/core/*`

Goal:
- establish `src/internhunter/config` and `src/internhunter/common` as the stable base
- keep current commands working
- do not change crawler, DB, LLM, or API behavior yet

### Phase 2: Storage Contracts

Move next:
- ORM models
- database sessions
- repository classes

Target code:
- `src/infrastructure/db/models.py`
- `src/infrastructure/db/session.py`
- `src/infrastructure/db/repositories/*`

Goal:
- isolate persistence boundaries
- keep raw job dedupe and clean job writes unchanged

### Phase 3: Orchestration

Move next:
- Prefect flow composition
- CLI entry points that call the flows

Target code:
- `src/flows/ingestion_flow.py`
- `src/infrastructure/prefect/*`
- `src/run_pipeline.py`
- `src/main.py`

Goal:
- keep the pipeline entry points stable while removing duplication

### Phase 4: Ingestion

Move next:
- crawler setup
- URL discovery
- job page extraction

Target code:
- `src/services/crawler/*`

Goal:
- preserve CSS-first extraction and raw fallback behavior
- preserve blocked-page audit handling

### Phase 5: Extraction and Embeddings

Move next:
- validation
- LLM parsing
- embedding generation

Target code:
- `src/services/job_processor/validator.py`
- `src/services/job_processor/job_processor.py`
- `src/services/job_processor/embedder.py`
- `src/infrastructure/llm/*`

Goal:
- preserve Gemini-first with Groq fallback
- preserve 768-dimension embeddings
- keep validation before parsing

### Phase 6: Search and Resume

Move next:
- structured search
- similarity search
- resume upload and matching

Target code:
- `src/infrastructure/db/repositories/search.py`
- `src/services/chat/tools.py`
- `src/services/chat/agent.py`

Goal:
- keep matching behavior stable before exposing any new public API

### Phase 7: API

Move last:
- chat routes
- future search routes

Target code:
- `src/infrastructure/api/routes/*`

Goal:
- expose cleaned-up service boundaries after the underlying modules are stable

## What To Do First, In Practice

If you are starting the refactor now, do this first:

1. Confirm `src/internhunter/config/settings.py` is the canonical config module.
2. Confirm `src/internhunter/common/logging.py` is the canonical logging module.
3. Add thin compatibility imports from the old paths if needed.
4. Add or update tests for config and logging import behavior.
5. Stop there and verify existing commands still work.

## What Not To Start With

Avoid these as the first refactor step:

- crawler logic
- extraction logic
- database schema changes
- embedding logic
- resume matching
- search ranking
- API route changes

Those areas are higher risk and depend on the shared foundation being stable first.

## Checkpoint Rule

After each phase:

- run the smallest useful test set
- record what still imports from the old path
- only then move to the next phase

## First 10 Commits

Each step below should be small enough to review independently.

1. Add `src/internhunter/config/settings.py` as the new config home.
2. Add `src/internhunter/common/logging.py` as the new logging home.
3. Add compatibility imports in legacy config/logging modules if needed.
4. Add a smoke test for the new foundation imports.
5. Move or wrap ORM models into the storage boundary.
6. Move the database session factory into the storage boundary.
7. Update repository tests to pin current storage behavior.
8. Choose the canonical orchestration path and make the other one legacy.
9. Move crawler config and crawler service behind the new package boundary.
10. Move validator, processor, and embedder in that order, keeping behavior unchanged.

## Commit Rules

- One commit = one narrow intent.
- Do not mix foundation, storage, and crawler changes in the same commit.
- If a commit changes imports, make sure the old import path still works or has a documented replacement.
- If a commit changes runtime behavior, add or update a test in the same commit.
- Stop immediately if a commit would require a schema change without a migration path.
