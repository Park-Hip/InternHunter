# Configuration

## Current Sources

- Environment variables are loaded from `.env` by `src/config/settings.py`.
- Runtime defaults and overrides are read from `src/config/settings.yaml`.
- Prompt templates are read from `src/config/prompts.yaml`.

## Main Settings

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `DB_URL`
- `DS_URL`
- `AIE_URL`
- `crawler.*`
- `llm.*`
- `agent.*`
- `logging.*`
- `mlflow.*`

## Notes

- The code uses `pydantic-settings`.
- TODO: verify whether any settings are overridden elsewhere at runtime.
