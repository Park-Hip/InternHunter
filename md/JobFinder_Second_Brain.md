---
tags:
  - etl
  - python
  - craw4ai
  - llm
  - prefect
  - database
  - vector-search
status: Active
date: 2026-05-12
---

# JobFinder Ingestion Pipeline: Deep Dive Technical Report

This document serves as a detailed technical reference for the JobFinder ETL pipeline. It outlines the specific mechanisms, code structures, and architectural decisions behind the ingestion of unstructured job postings into a structured, vector-searchable database.

---

## 1. System Architecture Overview

The pipeline is structured as an asynchronous, 3-phase ETL process orchestrated by Prefect. The core design philosophy separates the volatile act of web scraping from the expensive act of LLM processing, using a local SQLite database as a staging area.

**The Pipeline Flow (`src/flows/ingestion_flow.py`):**
1.  **Fetch Links:** Scrape search pages for job URLs.
2.  **Crawl Jobs:** Scrape the individual HTML/Markdown of each URL.
3.  **Process Jobs:** Run validation, LLM extraction, and embedding generation.

---

## 2. Phase 1: Acquire (The Crawler Module)
**Location:** `src/services/crawler/crawl.py`

The crawler uses `Craw4AI` and operates in a two-tiered asynchronous model to ensure reliability.

### 2.1. Link Fetching (`fetch_links_task`)
*   **Mechanism:** Navigates to search aggregate pages and extracts job URLs using CSS selectors.
*   **Duplicate Filtering:** Before doing a deep crawl, the `JobRepository.filter_new_links()` method normalizes the URLs (stripping queries/fragments) and cross-references them against the `RawJobDB` to drop duplicates instantly.

### 2.2. Detail Extraction (`crawl_jobs_task`)
*   **Mechanism:** Takes the deduplicated list of URLs and performs a deep crawl on each page.
*   **Storage:** The raw HTML or Markdown is extracted and dumped into the `raw_jobs` table via `JobRepository.save_raw_job()`. The job's status is marked as `pending`.
*   **Resilience:** The task handles its own concurrency and tracks success/failure metrics, updating the run context via `uuid4()` for logging traceability.

---

## 3. Phase 2: Validate & Transform (The Job Processor)
**Location:** `src/services/job_processor/job_processor.py`

This module is responsible for turning the raw HTML/Markdown into strictly typed JSON and generating vector embeddings. It fetches jobs from the database where `status == "pending"`.

### 3.1. Heuristic Validation (`JobValidator`)
*   Before spending money/tokens on an LLM, the system passes the `raw_markdown` through a pre-validation guardrail (`validator.is_valid`).
*   If validation fails, the job status is set to `failed` and it is routed to the Audit table (DLQ) with the reason.

### 3.2. LLM Extraction with Fallback (`llm_router`)
*   Valid jobs are passed to `router.process_with_fallback(job)`.
*   The router attempts to extract data using the primary LLM (Gemini). If it encounters API limits or failures, it automatically falls back to an alternative model (e.g., Groq).
*   **Quality Gate:** Post-extraction, the system checks for critical fields (`standardized_title`, `description`). If missing, it raises an `LLM_INCOMPLETE` error and fails the job.

### 3.3. Vector Embedding Generation
*   Once extracted, `Embedder().generate_embedding()` combines the `standardized_title`, `description`, and `technical_competencies` into a single text block.
*   This text is vectorized and prepped for storage alongside the structured job data.

---

## 4. Phase 3: Load & Storage (Database Architecture)
**Location:** `src/infrastructure/db/repository.py`

The database acts as the central state machine for the pipeline. It uses SQLAlchemy and separates raw ingestion data from clean, queryable data.

### 4.1. Core Tables
*   **`RawJobDB` (The Staging Area):** Stores the `url`, `raw_markdown`, and `status` (`pending`, `completed`, `failed`). This allows the crawler and the processor to operate independently at different speeds.
*   **`CleanJobDB` (The Data Warehouse):** Stores the final Pydantic-validated output (`job_level`, `tech_stack`, `salary_min/max`, `cities`). Crucially, it stores the generated `embedding` array.
*   **`AuditJobDB` (The Dead Letter Queue):** Acts as an audit trail for failures. Stores the `error_type` (e.g., `VALIDATION_FAILED`, `PROCESSING_ERROR`), the `error_message`, and a snippet of the `html_content` for debugging.

### 4.2. Vector Search Capabilities
*   The `JobRepository` exposes `search_jobs_by_similarity()`, which uses `pgvector`'s cosine similarity operator (`<=>`) to allow AI agents to semantically match user resumes against the `CleanJobDB.embedding` column.

---

## 5. Phase 4: Orchestration (Prefect)
**Location:** `src/flows/ingestion_flow.py`

Prefect glues the entire operation together, handling retries and failure states without manual intervention.

### 5.1. Task Decorators & Resilience
*   **`@task(retries=3, retry_delay_seconds=60)`:** The `fetch_links_task` is highly resilient to temporary network failures or rate limits on the target job board.
*   **`@task(retries=2, retry_delay_seconds=300)`:** The `crawl_jobs_task` waits a full 5 minutes before retrying to prevent IP bans.

### 5.2. Conditional Execution Flow
*   The `@flow` defines the dependency tree. 
*   `process_jobs_task` is only triggered if `fetch_links_task` successfully returned new links, saving compute time and logging noise when no new jobs are available.
