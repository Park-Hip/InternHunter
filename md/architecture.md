# InternHunter: Architectural Blueprint

## 1. High-Level Architecture
The system follows a **Modular Monolith** pattern, organized around functional layers. This ensures a clean separation of concerns while minimizing deployment complexity for the MVP.

```mermaid
graph TD
    subgraph "Data Ingestion Layer (Prefect)"
        A[craw4ai Scraper] --> B[LLM Structurer]
        B --> C[Data Sync Task]
    end

    subgraph "Persistence Layer (PostgreSQL)"
        C --> D[(PostgreSQL + pgvector)]
        D --> E[Repository Pattern]
    end

    subgraph "AI Agent Layer (LangChain)"
        F[User Message] --> G[Unified Agent]
        G --> H[SQL Tool]
        G --> I[Vector RAG Tool]
        H --> E
        I --> E
    end

    G --> J[User Response]
