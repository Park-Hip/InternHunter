# Deployment

## Current Paths

- Local CLI entry points in `src/main.py`
- Pipeline wrapper in `src/run_pipeline.py`
- Docker support via `Dockerfile` and `docker-compose.yml`

## Current Deployment Shape

- PostgreSQL runs in a container with `pgvector`.
- The app code is containerized separately from the database.
- The worker image installs Playwright browsers.

## Notes

- TODO: verify whether the Docker command path is current, because `Dockerfile` references a script module that is not present in the repo.
