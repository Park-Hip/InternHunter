# TopCV Fixtures

This folder holds representative TopCV-style job-detail fixtures for extraction contract tests.

Current purpose:
- validate structured job contract shape
- protect required fields for `ProcessedJob` / `LLMJobProcess`
- avoid live TopCV, live LLM, and live PostgreSQL during unit tests

Current fixtures:
- `normal_job.html`
- `normal_job.extracted.json`
- `missing_salary.html`
- `missing_salary.extracted.json`
- `negotiable_salary.html`
- `negotiable_salary.extracted.json`
- `multiple_locations.html`
- `multiple_locations.extracted.json`

Planned additions:
- internship/fresher
- expired/deadline edge case
- malformed page
- blocked/empty content
