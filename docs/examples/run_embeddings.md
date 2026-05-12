# Run Embeddings

The embedding path runs through the processing command:

```bash
uv run python src/run_pipeline.py --limit 10
```

## Notes

- Embeddings are created during job processing, not as a standalone public API.
- TODO: verify whether `src/scripts/backfill_embeddings.py` is currently used for maintenance jobs.
- `src/main.py` is no longer part of the supported command surface.
