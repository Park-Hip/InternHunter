# Run Embeddings

The embedding path runs through the processing command:

```bash
uv run python src/main.py process --limit 10
```

## Notes

- Embeddings are created during job processing, not as a standalone public API.
- TODO: verify whether `src/scripts/backfill_embeddings.py` is currently used for maintenance jobs.
