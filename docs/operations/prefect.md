# Prefect

## Current Use

- `src/flows/ingestion_flow.py` defines the main ingestion flow.
- `src/infrastructure/prefect/flows.py` defines an alternate production-oriented flow.
- `src/infrastructure/prefect/tasks.py` contains task wrappers.

## What Prefect Handles

- retries
- task boundaries
- flow-level orchestration
- pipeline run telemetry

## Notes

- TODO: verify which flow file should be treated as canonical.
- Keep orchestration changes separate from crawler and processor changes.
