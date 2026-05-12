# Search Architecture

Current search behavior is split across two paths:

- structured filtering through `SearchRepository.search_jobs_by_criteria()`
- vector similarity search through `SearchRepository.search_jobs_by_similarity()`

## Structured Search

- filters by title
- filters by job level
- filters by cities
- filters by experience
- returns mapped job summaries

## Similarity Search

- uses the `clean_jobs.embedding` column
- queries with pgvector cosine distance
- returns mapped job summaries for ranking by similarity

## Current Gaps

- There is no dedicated public search endpoint yet.
- `search_jobs_sql` and `match_jobs_resume` exist as chat tools, not as standalone API routes.
- TODO: verify from codebase whether a semantic search service layer exists outside the repository methods.
