# InternHunter: MVP Plan & Technical Specification

## 1. Goal
Build an automated job discovery platform that scrapes TopCV, structures data in PostgreSQL, and allows users to query jobs using natural language and resume-matching.

## 2. Component Design

### A. Data Ingestion (Scraper + Orchestrator)
- **Tech:** `crawl4ai`, `Prefect`.
- **Logic:** 
  - Daily cron job scrapes TopCV listings.
  - LLM-powered extraction converts raw HTML to structured JSON.
  - Idempotency check prevents duplicate processing.

### B. Storage (Relational + Vector)
- **Tech:** PostgreSQL, `pgvector`.
- **Tables:**
  - `raw_jobs`: Audit trail for raw HTML.
  - `clean_jobs`: Structured fields (title, salary, skills, city).
  - `job_embeddings`: Vector store for semantic search.
  - `user_profiles`: Stores parsed resume text and embedding.

### C. Agentic Search (The Brain)
- **Tech:** LangChain (Unified Agent).
- **Tools:**
  - `text_to_sql`: Converts user questions to SQL queries for analytics.
  - `resume_matcher`: Performs vector similarity search between user resume and job embeddings.
  - `resume_uploader`: Handles PDF/Docx parsing into the user profile.

## 3. Verification Plan
- **Pipeline:** Verify Prefect successfully triggers a flow and populates `clean_jobs`.
- **SQL Accuracy:** Test query "Top 5 skills for Python" against generated SQL.
- **RAG Relevance:** Verify top matches for a "Frontend Developer" resume are actually frontend roles.
