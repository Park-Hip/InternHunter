# 🗺️ "Set-and-Forget" Job Hunter - Industrial MVP Roadmap

> **Mission:** Build a zero-maintenance generic job hunter that ingests a CV, scrapes the web, smartly matches opportunities using AI, and delivers actionable leads directly to the user.

## 🏗️ System Architecture

```mermaid
graph TD
    User[User] -->|Upload PDF| CV_Engine[Pillar 1: CV Ingestion Engine]
    CV_Engine -->|Extract & Vectorize| UserProfile[(User Profile & Embeddings)]
    
    WebScraper[Phase 1: Raw Scraper] -->|Raw HTML| RawDB[(SQLite: Raw Jobs)]
    
    RawDB -->|Batch Process| Refinery[Pillar 2: Data Refinery / ETL]
    Refinery -->|LLM Extraction (Gemini)| CleanDB[(SQLite: StandardJobs)]
    
    UserProfile --> Matcher[Pillar 3: The Brain]
    CleanDB --> Matcher
    
    Matcher -->|Filter & Rank| Top10[Top 10 Matches]
    
    Top10 -->|Push| Discord[Pillar 4a: Discord Alert]
    Top10 -->|Visualize| Streamlit[Pillar 4b: Streamlit Dashboard]
```

---

## 🚀 Phase 2: The CV Ingestion Engine
**Goal:** Convert a static PDF resume into a dynamic "Search Vector" and structured "Skills Profile".

### 🛠️ Tech Stack (Free & Open Source)
*   **PDF Parsing:** `PyMuPDF` (aka `fitz`) - _(Faster and more accurate text block extraction than PyPDF2)_.
*   **Vector Embeddings:** `sentence-transformers` (HuggingFace) - Model: `all-MiniLM-L6-v2` _(Lightweight, fast, 384d vectors)_.
*   **Pydantic:** Type-safe schema for the user profile.

### 📋 Workflow
1.  **Read:** Load `resume.pdf` using `PyMuPDF`.
2.  **Clean:** Remove header/footer noise, normalize whitespace.
3.  **Chunk:** Split text into semantic chunks (e.g., "Experience", "Skills", "Projects").
4.  **Vectorize:** Generate a 384-dimensional dense vector for the **entire resume text** (for semantic matching).
5.  **Extract Skills:** Use a simple keyword dictionary or small LLM prompt to exact specific tech tags (e.g., `['Python', 'AWS', 'Docker']`) for hard filtering.
6.  **Store:** Save as `user_profile.json` (easy to edit/tune) + `user_embedding.npy`.

---

## 🏭 Phase 3: The Data Refinery (ETL)
**Goal:** Transmute "Raw HTML" garbage into "StandardJob" gold.

### 🛠️ Tech Stack
*   **Extraction:** **Google Gemini 2.0 Flash API** (Free Tier).
    *   *Why?* It has a generous free tier (15 RPM), 1M context window (cheap), and is smart enough to handle messy HTML structure better than Regex.
*   **Validation:** `Pydantic` (already used in `JobParser`).
*   **Reliability:** `Tenacity` (for retry logic/backoff).
*   **Database:** `SQLite` (Upgrade existing DB to include a `parsed_jobs` table).

### 📋 Workflow
1.  **Fetch:** Select unparsed rows from `RawDB` (`WHERE parsed_at IS NULL`).
2.  **Pre-process:** Strip huge HTML tags, headers, and scripts to reduce token count.
3.  **LLM Call:** Send `JobModel` (description) -> Gemini Flash -> `JobParser` (JSON Schema).
    *   *Prompt Strategy:* "Extract the following fields. If not found, return null. Be strict about Salary parsing."
4.  **Validate:** Pydantic ensures types are correct (e.g., Salary is a `float`, not "Competitive").
    *   *Failure Mode:* If Pydantic fails, flag job as `parse_error` to avoid retry loops.
5.  **Upsert:** Save clean data to `StandardJobs` table; mark raw row as parsed.

---

## 🧠 Phase 4: The Brain (Scoring & Matching)
**Goal:** Intelligently rank 1000s of jobs to find the "Top 10" for **YOU**.

### 🛠️ Tech Stack
*   **Vector Search:** `scikit-learn` (Cosine Similarity) or simple `numpy` dot product.
    *   *Why Not Vector DB?* For <100k jobs, in-memory numpy operations are millisecond-fast and $0 cost. No need for Pinecone/Milvus overhead.
*   **Traditional ML:** `TfidfVectorizer` (optional, if semantic search feels too "fuzzy").
*   **Logic:** Python `pandas`.

### 📋 Matching Strategy (The "Hybrid Score")
Every job gets a generic `MatchScore` (0-100%):

1.  **Hard Filters (Pass/Fail):**
    *   *Salary:* `Job.salary_max >= User.min_salary` (or if `null`, pass with penalty).
    *   *Location:* `Job.city IN User.cities` (or Remote).
    *   *Experience:* `Job.min_yoe <= User.yoe + 1` (Allow some stretch).
    *   **Result:** Eliminate 80% of noise immediately.

2.  **Semantic Score (The "Vibe" Check):**
    *   Compute Cosine Similarity(`Job_Description_Vector`, `Resume_Vector`).
    *   *Captures:* "Data Scientist working on NLP" vs "Data Analyst working on Excel", even if keywords overlap.

3.  **Keyword Score (The "Skill" Check):**
    *   Jaccard Similarity of `Job.tech_stack` vs `User.tech_stack`.
    *   *Captures:* "Must have Python + AWS".

4.  **Final Formula:**
    ```python
    FinalScore = (SemanticScore * 0.6) + (KeywordScore * 0.4)
    if not HardFilters: FinalScore = 0
    ```

---

## 🖥️ Phase 5: The Interface (Delivery)
**Goal:** Consumption. Deep operational insight + Daily quick alerts.

### 🅰 Option A: Set-and-Forget (Daily Alerts)
*   **Tech:** `Discord Webhooks` (Free, easy to format).
*   **Workflow:**
    *   Script runs at 8:00 AM.
    *   Calculates Top 10 matches.
    *   Sends a rich Embed to a private Discord channel.
    *   **Action Buttons:** "Apply Now" (Link), "Dismiss" (Feedback loop).

### 🅱 Option B: The "War Room" Dashboard
*   **Tech:** `Streamlit` (Python-native, rapid prototyping).
*   **Features:**
    *   **Job Feed:** Sortable table of matches with "Why it matched" tooltips.
    *   **Market Radar:** Bar charts of "Top Skills in Demand" vs "Skills I Have".
    *   **Salary Trend:** Line chart of scraped salaries over time.
    *   **Missing Link:** "If you learn **Kafka**, you unlock 15 more jobs."

---

## 📅 Execution Plan

*   ✅ **Phase 1:** Raw Data Layer (Done)
*   [ ] **Phase 2:** CV Ingestion (Est. 1 Day)
*   [ ] **Phase 3:** ETL Pipeline with Gemini (Est. 2 Days)
*   [ ] **Phase 4:** Matching Logic (Est. 2 Days)
*   [ ] **Phase 5:** Discord Bot + Streamlit UI (Est. 2 Days)

**Total Time to MVP:** ~1 Week
