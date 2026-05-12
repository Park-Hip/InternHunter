# API Errors

## Current Behavior

- Most HTTP failures are converted to `500 Internal server error occurred.`
- The chat route logs the underlying exception before returning the generic response.

## Data-Layer Failure Types

These appear in `audit_jobs.error_type`:

- `BOT_DETECTED`
- `CRAWL_FAILED`
- `VALIDATION_FAILED`
- `LLM_INCOMPLETE`
- `PROCESSING_ERROR`

## TODO

- TODO: define a real API error contract once endpoints beyond chat are stable.
