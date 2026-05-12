# Deployment

## Current Paths

- Pipeline wrapper in `src/run_pipeline.py`
- Canonical Prefect flows in `src/internhunter/orchestration/`
- Maintenance scripts under `src/scripts/` when still used
- Docker support via `Dockerfile` and `docker-compose.yml`

## Removed Path

- `src/main.py` was intentionally removed as a user-facing CLI entry point.

## Current Deployment Shape

- PostgreSQL runs in a container with `pgvector`.
- The app code is containerized separately from the database.
- The worker image installs Playwright browsers.

## Notes

- TODO: verify whether the Docker command path is current, because `Dockerfile` references a script module that is not present in the repo.
