# Architecture Overview

InternHunter is currently organized like a modular monolith:

- orchestration lives in Prefect flows and CLI entry points
- business logic lives in services
- external integrations live in infrastructure modules
- shared types live in `src/core`

## Main Flow

TopCV listing pages -> job detail pages -> raw storage -> validation -> LLM extraction -> clean jobs -> embeddings -> search and matching

## Main Layers

- `src/config/` for settings and prompts
- `src/core/` for shared models and utilities
- `src/services/` for crawler, processor, and chat behavior
- `src/infrastructure/` for DB, LLM, logging, API, and Prefect adapters
- `src/flows/` for orchestration

## TODO

- TODO: verify from codebase which flow file is canonical for production use.
