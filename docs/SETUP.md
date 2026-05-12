# Setup

## Prerequisites

- Python 3.12+
- `uv`
- PostgreSQL with `pgvector`
- Docker and Docker Compose if you want the bundled database container

## Environment

Create a `.env` file in the project root. The current code reads:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `DB_URL`

The repository also uses YAML config files:

- `src/config/settings.yaml`
- `src/config/prompts.yaml`

## Common Commands

```bash
uv sync
docker-compose up -d
uv run python src/scripts/upgrade_db.py
uv run python src/run_pipeline.py --limit 10
uv run python src/scripts/run_production_v2.py
```

## Notes

- `docker-compose.yml` starts PostgreSQL with `pgvector`.
- `src/scripts/upgrade_db.py` is the current schema upgrade helper.
- `src/main.py` is intentionally removed; use `src/run_pipeline.py`, canonical Prefect flows, or scripts under `src/scripts/` instead.
- TODO: verify whether `src/flows/ingestion_flow.py` or `src/internhunter/orchestration/ingestion_flow.py` should be treated as the canonical pipeline entry point for direct imports.
