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
uv run python src/main.py crawl
uv run python src/main.py process --limit 10
uv run python src/main.py init-db
uv run python src/main.py serve --host 0.0.0.0 --port 8000
```

## Notes

- `docker-compose.yml` starts PostgreSQL with `pgvector`.
- `src/scripts/upgrade_db.py` is the current schema upgrade helper.
- TODO: verify whether `src/flows/ingestion_flow.py` or `src/run_pipeline.py` should be treated as the canonical pipeline entry point.
