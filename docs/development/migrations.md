# Migrations

## Current State

- Schema changes are currently handled by `src/scripts/upgrade_db.py`.
- Tables are also created from ORM metadata through repository initialization.

## Rules

- Add a migration or upgrade path before changing persisted fields.
- Do not rely on ad hoc manual database edits.
- Verify new columns against existing data before shipping a refactor.

## TODO

- Add Alembic when the schema starts changing more often.
