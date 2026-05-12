# InternHunter Docs

InternHunter is an automated job discovery and resume-matching platform for TopCV listings.

This docs set is meant to support safe refactoring:
- it describes the code as it exists now
- it separates implemented behavior from planned work
- it keeps module boundaries and data contracts explicit

## Start Here

- [SETUP.md](./SETUP.md) for local setup and common commands
- [CURRENT_BEHAVIOR.md](./CURRENT_BEHAVIOR.md) for what works today
- [REFACTORING.md](./REFACTORING.md) for safe refactor sequencing
- [ROADMAP.md](./ROADMAP.md) for planned work

## Architecture

- [architecture/overview.md](./architecture/overview.md)
- [architecture/module_boundaries.md](./architecture/module_boundaries.md)
- [architecture/etl_pipeline.md](./architecture/etl_pipeline.md)
- [architecture/database_schema.md](./architecture/database_schema.md)
- [architecture/data_contracts.md](./architecture/data_contracts.md)
- [architecture/search_architecture.md](./architecture/search_architecture.md)
- [architecture/resume_matching.md](./architecture/resume_matching.md)

## Operations

- [operations/configuration.md](./operations/configuration.md)
- [operations/prefect.md](./operations/prefect.md)
- [operations/deployment.md](./operations/deployment.md)
- [operations/monitoring.md](./operations/monitoring.md)
- [operations/troubleshooting.md](./operations/troubleshooting.md)

## Development

- [development/testing.md](./development/testing.md)
- [development/code_style.md](./development/code_style.md)
- [development/migrations.md](./development/migrations.md)
- [development/logging.md](./development/logging.md)
- [development/ai_workflow.md](./development/ai_workflow.md)

## API

- [api/models.md](./api/models.md)
- [api/endpoints.md](./api/endpoints.md)
- [api/errors.md](./api/errors.md)

## Examples

- [examples/local_ingestion.md](./examples/local_ingestion.md)
- [examples/run_scraper.md](./examples/run_scraper.md)
- [examples/run_embeddings.md](./examples/run_embeddings.md)
- [examples/search_examples.md](./examples/search_examples.md)
