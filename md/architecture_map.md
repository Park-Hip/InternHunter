# InternHunter: System Architecture & Workflow Map

This document outlines the complete architecture of the InternHunter project, mapping out current modules, their files, and architectural patterns. It serves as a blueprint to systematically evaluate system design, assess robustness, and identify missing components required to reach a "finished" production state.

## 1. The "Best Outcome": A Finished Workflow Pipeline

To be considered complete and highly robust, the end-to-end workflow must achieve the following capabilities:

1.  **Fully Automated Orchestration:** The crawler and processor run on a scheduled basis (e.g., daily via Prefect) without manual CLI intervention. The system dynamically bypasses anti-bot measures and issues alerts for persistent failures.
2.  **Resilient ETL & Embeddings:** Unstructured data is transformed into the Pydantic schema using the LLM Router with near 100% uptime (seamless failovers). High-quality vector embeddings are generated for *every* parsed job.
3.  **True Semantic RAG:** The chat agent utilizes `pgvector` natively. It goes beyond exact keyword SQL filters (e.g., `cities = 'Hanoi'`) to understand semantic intent (e.g., "Find me a backend role suitable for someone transitioning from data analytics").
4.  **Observability & Telemetry:** Every pipeline run, LLM token usage, and crawler failure is tracked via MLflow and centralized logging. Dashboards exist to monitor system health.
5.  **Interactive User Interface:** A responsive frontend (e.g., React/Next.js) exists for users to chat with the agent, view rich job cards, and provide feedback on recommendations.

---

## 2. Module Inventory & Architecture Map

Use this map to methodically audit the code for system design and robustness.

### A. Data Ingestion Module (Crawler)
*   **Status:** ✅ Functional | 🚧 Needs Orchestration
*   **Architecture Pattern:** Asynchronous Batch Processor with Exponential Backoff.
*   **Core Files:**
    *   `src/services/crawler/crawl.py`: The core engine. Manages async browser contexts (`UndetectedAdapter`), implements `tenacity` retry logic, and filters duplicate links against the database before scraping.
    *   `src/services/crawler/crawl_config.py`: Playwright/crawl4ai configurations (headers, timeouts, DOM selectors).
*   **Robustness Checks for Later:**

    *   *Selector Fragility:* Will the pipeline fail gracefully or alert immediately if the target job board changes its HTML layout?

### B. Transformation & Enrichment Module (Job Processor)
*   **Status:** ✅ Functional | 🚧 Needs Embedding Optimization
*   **Architecture Pattern:** ETL Transformer.
*   **Core Files:**
    *   `src/services/job_processor/job_processor.py`: Orchestrates fetching unparsed jobs from the DB, passing them to the LLM, generating embeddings, and saving the structured result.
    *   `src/services/job_processor/embedder.py`: Handles dense vector generation from the parsed text.
    *   `src/core/models/job.py`: Defines the strict Pydantic schemas (`LLMJobProcess`, `ProcessedJob`) that the LLM is forced to output.
*   **Robustness Checks for Later:**
    *   *Dead-Letter Queue (DLQ):* What happens to a job if the LLM repeatedly fails to parse it? Are these isolated for manual review?
    *   *Rate Limiting:* Is the `time.sleep()` logic sufficient, or should embedding generation be batched?

### C. LLM Infrastructure Module
*   **Status:** ✅ Functional
*   **Architecture Pattern:** Strategy / Fallback Router Pattern.
*   **Core Files:**
    *   `src/infrastructure/llm/router.py`: The brain of the fallback mechanism. Attempts primary LLM, catches specific exceptions, and shifts to secondary providers.
    *   `src/infrastructure/llm/providers.py`: Concrete implementations for interacting with specific providers (Gemini, Groq, LiteLLM).
    *   `src/infrastructure/llm/prompt_registry.py` & `prompts/`: Centralized management for system prompts.
*   **Robustness Checks for Later:**
    *   *Cost Management:* Is token usage tracked per provider to monitor ETL costs?
    *   *Caching:* Can identical prompts be cached to save API calls?

### D. Persistence & Storage Module (Database)
*   **Status:** ✅ Functional
*   **Architecture Pattern:** Repository Pattern.
*   **Core Files:**
    *   `src/infrastructure/db/repository.py`: Abstracts all SQLAlchemy logic. Handles data ingestion, sequence syncing (to prevent ID collisions), and dynamic query building for tools.
    *   `src/infrastructure/db/models.py`: Defines the dual-schema (`RawJobDB` for auditability, `CleanJobDB` for search) and chat memory schemas.
    *   `src/infrastructure/db/session.py`: Connection pooling.
*   **Robustness Checks for Later:**
    *   *Migrations:* Implement `Alembic` for safe, version-controlled schema upgrades.
    *   *Text-to-SQL Safety:* Implement a Text-to-SQL pipeline for dynamic querying that includes strict validation/sanitization to prevent destructive operations (SQL Injection, DROPs, DELETEs) rather than relying on static SQL filters.
    *   *Vector Indexing:* Ensure `pgvector` columns have HNSW or IVFFlat indexes applied to speed up similarity searches as the DB grows.

### E. AI Agent & Serving Module (Chat)
*   **Status:** 🚧 Partially Functional (SQL tools work, Semantic Search is missing)
*   **Architecture Pattern:** Tool-Calling Agent / REST API.
*   **Core Files:**
    *   `src/services/chat/agent.py`: The conversational loop. Initializes memory, fetches system prompts (via MLflow), executes tool calls, and enforces max iteration depths.
    *   `src/services/chat/tools.py`: Defines the tools (functions) exposed to the LLM. Currently contains `search_jobs` (SQL-based filtering).
    *   `src/services/chat/tool_registry.py`: Decorator-based registry (`@register_tool`) to dynamically load tools.
    *   `src/services/chat/memory.py`: Manages session-based chat history in PostgreSQL.
    *   `src/infrastructure/api/routes/chat_routes.py`: FastAPI endpoints.
*   **Robustness Checks for Later:**
    *   *Vector Tooling:* **Critical.** Implement a `semantic_search_jobs` tool that calculates the embedding of the user's query and performs a Cosine Similarity search against `CleanJobDB.embedding`.
    *   *Context Window Management:* If a chat session gets too long, does `memory.py` summarize older messages to prevent exceeding token limits?

### F. Missing Modules Required for the "Finished" State
1.  **Orchestration Module (`src/prefect`):** The folder exists, but Prefect DAGs/Flows need to be explicitly defined to schedule the `crawl` -> `process` -> `index` sequence automatically.
2.  **Frontend / UI Module:** A user-facing client (React, Vue, or Streamlit) to interact with the FastAPI chat endpoints and display job results cleanly.
3.  **RAG Evaluation Module:** A testing pipeline (using tools like Ragas or TruLens) to quantitatively evaluate the Agent's answers for context relevance, faithfulness, and hallucination rates before pushing prompt changes to production.
