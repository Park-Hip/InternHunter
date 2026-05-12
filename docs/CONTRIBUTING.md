# Contributing

## Working Rules

- Read the relevant docs before editing code.
- Keep diffs small and focused on one module at a time.
- Do not make unrelated edits in the same change.
- Add or update tests when behavior changes.
- Do not change database schema without a migration or upgrade step.
- Do not add dependencies without a clear reason.

## Refactor Style

- Prefer move-only refactors first.
- Preserve behavior until the code is covered by tests.
- Use existing patterns for logging, config, and repositories.
- Update docs when behavior changes.

## Branch and Commit Shape

- One logical change per commit or checkpoint.
- Separate documentation-only changes from runtime code changes when possible.
- Capture a checkpoint before any behavior-changing step.

## Testing Expectation

- Unit tests should cover pure logic and mapping.
- Integration tests should cover the ETL flow and database writes.
