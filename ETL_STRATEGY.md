# 🏭 Phase 3: The Data Refinery (ETL Strategy)

> **Document Status:** Draft for Review
> **Goal:** Transform "Raw HTML Garbage" into "Structured Job Gold" reliably and cheaply.

## 1. Architectural Options

We are building an "Industrial MVP". We need high-quality data (which requires LLMs) but essentially zero cost. Here are the three paths:

### Option A: The "Local & Lean" (Strict MVP)
*   **Philosophy:** "If it runs on my laptop offline, it's good enough."
*   **Tech Stack:** `spaCy` (NLP), `Regular Expressions` (Regex), `BeautifulSoup` (HTML cleaning).
*   **Pros:** 
    *   ⚡ Fastest execution (Local CPU).
    *   💸 $0 Cost forever.
    *   🔒 Privacy (Data never leaves machine).
*   **Cons:**
    *   ❌ **Brittle:** Fails on new layouts or weird formatting.
    *   ❌ **Low Quality:** Hard to extract subtle things like "Salary Negotiable" or complex tech stacks without writing 1000s of Regex rules.
*   **Complexity:** Low (Scripting) -> High (Maintenance hell).

### Option B: The "Cloud Native" (Recommended 🌟)
*   **Philosophy:** "Let the AVIs do the heavy lifting, but don't pay for it."
*   **Tech Stack:** `Google Gemini 2.0 Flash` (Free Tier), `Pydantic` (Validation), `Tenacity` (Retries), `DiskCache` (Caching).
*   **Pros:**
    *   🧠 **Smart:** Understands context (e.g., knows "React" usually implies "JavaScript").
    *   🛠️ **Robust:** Handles broken HTML gracefully.
    *   💸 **Free-ish:** Gemini Flash has a generous free tier (15 RPM is enough for batching).
*   **Cons:**
    *   ⏳ **Slower:** Network latency + Rate Limits (requires sleeping).
    *   🔗 **Dependency:** Relies on Google API uptime.
*   **Complexity:** Medium (Requires async/await, rate limit management).

### Option C: The "Industrial Scale" (Overkill)
*   **Philosophy:** "Prepare for 10 million jobs."
*   **Tech Stack:** `Apache Airflow` (Orchestration), `RabbitMQ` (Queue), `Docker`, `PostgreSQL` (Vector DB).
*   **Pros:**
    *   🚀 **Unstoppable:** Indestructible pipeline.
    *   🔄 **Scalable:** Horizontal scaling workers.
*   **Cons:**
    *   💸 **Expensive**: Requires always-on infra.
    *   🤯 **Complex**: Deployment nightmare for a single developer.
*   **Complexity:** Very High.

---

## 2. The File Blueprint (Based on Option B)

We will adopt **Option B** to get "Industrial Grade" data quality without the "Industrial Scale" infrastructure overhead.

**Directory:** `src/etl/`

| File | Purpose |
| :--- | :--- |
| **`pipeline.py`** | **The Conductor.** The main entry point. Fetches `unparsed` jobs from DB, loops through them, manages the `processing_queue`, and handles graceful shutdowns. |
| **`cleaners.py`** | **The Janitor.** Non-LLM text processing. Strips HTML tags, removes aggressive whitespace, truncates huge descriptions *before* sending to LLM (saves tokens). |
| **`extractor.py`** | **The Translator.** The interface to Gemini. Contains the prompt engineering and the API call logic. Handles the specific "HTML -> JSON" transformation. |
| **`client.py`** | **The Gateway.** A robust wrapper around the Gemini API client. Handles authentication, **Rate Limiting (15 RPM)**, and retries (Tenacity). |
| **`repository.py`** | **The Librarian.** Handles database IO. `fetch_unparsed_jobs()`, `save_parsed_job()`, `mark_job_failed()`. Keeps SQL out of the logic. |
| **`models.py`** | **The Blueprint.** (Or reuse `src/schema/schema.py`). Defines the input `RawJob` and output `StandardJob` data classes. |

---

## 3. Minimum Viable Features (MVP Goals)

To consider Phase 3 "Done", the system must:

1.  **Strict Salary Parsing:** Convert "15tr - 20tr" or "$1k - $2k" into float values (`salary_min`, `salary_max`) and a currency code. Null if not found.
2.  **Tech Stack Array:** reliably extract `['Python', 'Django']` from a wall of text.
3.  **Idempotency:** If I run the script twice, it doesn't pay for/process the same job twice.
4.  **Error Jail:** If a job causes a crash (pydantic validation error), it gets marked `status='failed'` and skipped next time (doesn't block the pipeline).
5.  **Rate Limit Governor:** The system **automatically** sleeps/waits to stay under the Gemini Free Tier limits.

---

## 4. Scalability & Future Roadmap (The "Later" Pile)

*   **Schema Drift Detection:** (Later) Alerting if the output JSON structure changes (unlikely with Pydantic).
*   **Resume-Specific Tuning:** (Later) Fine-tuning the extraction to specifically look for skills *I* have.
*   **Vector Database:** (Later) Moving from SQLite to pgvector if we exceed 100k jobs.
*   **Orchestration UI:** (Later) Monitoring dashboard for the ETL process (for now, CLI logs are fine).

## 5. Decision Required
**Do you approve Option B (Cloud Native)?**
If yes, I will begin implementing the `src/etl/` module structure.
