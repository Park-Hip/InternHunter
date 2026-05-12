# Refactoring Status

## Current Status

The project has completed the boundary-creation stage. `src/internhunter/` is now the canonical namespace for new development.

Wrapper collapse is intentionally paused for now. Canonical modules exist, but several of them still delegate to legacy implementations under `src/services/`, `src/infrastructure/`, or `src/flows/`.

## Completed Boundaries

- `src/internhunter/config`
- `src/internhunter/common`
- `src/internhunter/storage`
- `src/internhunter/orchestration`
- `src/internhunter/ingestion`
- `src/internhunter/extraction`
- `src/internhunter/embeddings`
- `src/internhunter/llm`
- `src/internhunter/search`
- `src/internhunter/chat`
- `src/internhunter/resume`
- `src/internhunter/api`

## Current Architecture State

The canonical namespace is stable for imports and testing. Some modules are still wrapper-based so the system can keep working while the legacy implementation remains in place.

This was intentional: boundaries were created first so future work can be isolated, tested, and collapsed one module at a time.

## Wrapper-Based Areas

The following canonical paths still delegate to legacy modules:

- `src/internhunter/ingestion/crawl.py` -> `src.services.crawler.crawl`
- `src/internhunter/ingestion/crawl_config.py` -> `src.services.crawler.crawl_config`
- `src/internhunter/extraction/validator.py` -> `src.services.job_processor.validator`
- `src/internhunter/extraction/job_processor.py` -> `src.services.job_processor.job_processor`
- `src/internhunter/embeddings/embedder.py` -> `src.services.job_processor.embedder`
- `src/internhunter/llm/base.py` -> `src.infrastructure.llm.base`
- `src/internhunter/llm/providers.py` -> `src.infrastructure.llm.providers`
- `src/internhunter/llm/router.py` -> `src.infrastructure.llm.router`
- `src/internhunter/chat/tools.py` -> `src.services.chat.tools`
- `src/internhunter/chat/memory.py` -> `src.services.chat.memory`
- `src/internhunter/chat/tool_registry.py` -> `src.services.chat.tool_registry`
- `src/internhunter/chat/agent.py` -> `src.services.chat.agent`
- `src/internhunter/resume/matching.py` -> `src.services.chat.tools`

## Known Test Debt

- Some integration tests require a live PostgreSQL database and are skipped unless `RUN_DB_TESTS=1`.
- Some tests still verify legacy compatibility paths on purpose.
- Manual scripts under `src/scripts/` are not part of normal pytest collection.
- A few smoke tests still exist specifically to prove canonical imports resolve during the transition.

## Known Lint Debt

- There may still be residual Ruff noise in legacy scripts and compatibility modules.
- Some compatibility wrappers are intentionally minimal and may still trigger import-related lint noise if collapsed too early.
- Cleanup should stay incremental and test-backed.

## Known Design Debt

- Several wrappers can eventually be collapsed.
- `match_score` still has placeholder behavior.
- Chat memory persistence needs later review.
- Search ranking should be redesigned later.
- Resume matching should be separated more cleanly from chat tools later.
- Job extraction still needs stronger fixture-based validation.

## What Not To Do Next

- Do not collapse all wrappers at once.
- Do not redesign search ranking yet.
- Do not rewrite chat agent or memory yet.
- Do not change database schema during cleanup.
- Do not mix product improvements with structural collapse.
- Do not remove compatibility paths until tests and consumers have migrated.

## Recommended Next Task

Focus on job extraction reliability.

Suggested next work:

1. Collect 5 to 10 saved TopCV job-detail HTML fixtures.
2. Add fixture-based extraction tests.
3. Define the required extracted fields for a valid processed job.
4. Ensure extraction tests do not depend on live network or live LLM calls.
5. Improve validation failure reporting where it helps debugging extraction.
6. Only then consider extraction logic changes.

This is the best next product-quality task because it improves the reliability of the most failure-prone stage without destabilizing the established boundaries.

## Verification Commands

- `uv run pytest tests/unit/test_canonical_boundaries_smoke.py -q`
- `uv run pytest tests/unit/test_supported_entrypoints.py -q`
- `uv run pytest -q`
