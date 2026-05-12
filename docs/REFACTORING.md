# Refactoring

## Safe Order

1. Read the relevant docs and tests.
2. Add or strengthen tests around the current behavior.
3. Make a move-only refactor in one module.
4. Run the smallest useful verification step.
5. Commit or checkpoint.
6. Only then move to the next module.

## Module-by-Module Rule

- Change one module at a time whenever possible.
- Do not mix crawler, processor, DB, and API edits in one refactor unless the change is purely mechanical.
- Keep orchestration changes separate from business-logic changes.

## Move-Only Refactors

- Rename files or classes without changing behavior.
- Extract helpers.
- Reorder code for clarity.
- Split large modules into smaller files while preserving imports and behavior.

## Behavior-Changing Refactors

- Validation logic changes.
- Extraction or fallback logic changes.
- Schema or contract changes.
- Search or matching ranking changes.
- API contract changes.

## Checkpoint Rules

- Stop after each meaningful module boundary.
- Record what changed and what still needs verification.
- Do not stack multiple risky changes without an intervening test run.
- If a change touches the database schema, include a migration or upgrade path before merging.
