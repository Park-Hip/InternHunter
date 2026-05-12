# AI-Assisted Refactoring Workflow

## Rules

- Read the docs before changing code.
- Keep diffs small.
- Do not make unrelated edits.
- Add or update tests for any behavior change.
- Do not change the database schema without a migration or upgrade path.
- Do not add dependencies without justification.

## Practical Workflow

1. Inspect the current module boundaries.
2. Identify the smallest safe change.
3. Make the change.
4. Verify with the narrowest useful test set.
5. Record any TODOs that remain.

## Guardrails

- Prefer move-only refactors first.
- Avoid changing more than one subsystem in a single AI-assisted pass.
- If a change touches a contract, update the matching docs and tests together.
