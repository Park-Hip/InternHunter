# TopCV Fixtures

This folder holds representative TopCV-style job-detail fixtures for extraction contract tests.

Current purpose:
- validate structured job contract shape
- protect required fields for `ProcessedJob` / `LLMJobProcess`
- avoid live TopCV, live LLM, and live PostgreSQL during unit tests

Current fixtures:
- `normal_job.html`
- `normal_job.extracted.json`

Planned additions:
- missing salary
- negotiable salary
- multiple locations
- internship/fresher
- expired/deadline edge case
- malformed page
- blocked/empty content
