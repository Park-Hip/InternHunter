import sqlite3
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Dict

from src.settings.settings import LOGS_DIR, DATA_DIR
from src.schema.schema import StandardJob  # Assuming you renamed JobParser to StandardJob
from src.utils.utils import normalize_url

# Setup Logger
log_filename = f"{LOGS_DIR}/pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

class JobDatabase:
    def __init__(self, db_path: Path | str = None):
        # Allow overriding path for testing, default to settings path
        if db_path is None:
            self.db_path = (DATA_DIR / "db" / "jobs.db").resolve()
        else:
            self.db_path = Path(db_path).resolve()
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None

    def __enter__(self):
        """Context manager entry: 'with JobDatabase() as db:'"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: Auto-close connection."""
        self.close()

    def connect(self):
        """Opens connection if not open."""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            # PRO TIP: This allows accessing columns by name (row['url'])
            self.conn.row_factory = sqlite3.Row

    def close(self):
        """Closes connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        """Creates necessary tables."""
        self.connect()
        cursor = self.conn.cursor()

        # Raw Jobs Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS raw_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            company TEXT,
            full_json_dump TEXT,
            scraped_at TEXT,
            source TEXT,
            is_processed BOOLEAN DEFAULT 0
        )
        ''')

        # Clean/Standardized Jobs Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clean_jobs (
                id INTEGER PRIMARY KEY,
                url TEXT,
                standardized_title TEXT,
                job_level TEXT,
                is_internship INTEGER,        
                cities TEXT,                
                min_years_experience REAL,    
                min_gpa REAL,
                english_requirement TEXT,
                salary_min REAL,
                salary_max REAL,
                is_salary_negotiable INTEGER, 
                tech_stack TEXT,             
                domain_knowledge TEXT,   
                FOREIGN KEY(id) REFERENCES raw_jobs(id)
            )
        ''')
        self.conn.commit()
        logger.info(f"DB initialized at {self.db_path}")

    def get_raw_job_count(self) -> int:
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT COUNT(*) FROM raw_jobs''')
        return cursor.fetchone()[0]

    def filter_new_links(self, raw_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Returns only the links that are NOT in the database."""
        self.connect()
        cursor = self.conn.cursor()

        cursor.execute('''SELECT url FROM raw_jobs''')
        # DB stores normalized URLs
        existing_urls = set(row['url'] for row in cursor.fetchall() if row['url'])

        new_links = []
        seen_norm = set()
        
        for link in raw_links:
            norm = normalize_url(link.get("url"))
            if not norm:
                continue
            
            # Dedupe within this batch
            if norm in seen_norm:
                continue
            seen_norm.add(norm)

            if norm not in existing_urls:
                link["url"] = norm
                new_links.append(link)

        return new_links

    def save_raw_job(self, job_data: Dict[str, Any]) -> bool:
        """Saves a raw job to the database."""
        required = ("url", "title", "company")
        for key in required:
            val = job_data.get(key)
            if val is None or not str(val).strip():
                logger.warning(f"Refusing to save job: missing or empty '{key}'")
                return False

        self.connect()
        clean_link = normalize_url(job_data["url"])
        title = self._sanitize_text(job_data.get("title"))
        company = self._sanitize_text(job_data.get("company"))

        dump_data = job_data.copy()
        dump_data["title"] = title
        dump_data["company"] = company

        try:
            self.conn.cursor().execute('''
                INSERT OR IGNORE INTO raw_jobs 
                (url, title, company, full_json_dump, scraped_at, source) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                clean_link,
                title,
                company,
                json.dumps(dump_data, ensure_ascii=False),
                datetime.now().isoformat(),
                "topcv"
            ))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"DB Error save_raw_job: {e}")
            return False

    def save_clean_job(self, url: str, analysis: StandardJob) -> bool:
        """Saves the Pydantic model to the clean_jobs table."""
        self.connect()
        try:
            # Get ID from raw_jobs
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM raw_jobs WHERE url = ?", (url,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"Cannot save clean job: URL not found in raw_jobs: {url}")
                return False
            
            raw_id = row['id']
            
            # Save to clean_jobs
            cursor.execute('''
                INSERT OR REPLACE INTO clean_jobs (
                    id, url, 
                    standardized_title, job_level, is_internship, cities,
                    min_years_experience, min_gpa, english_requirement,
                    salary_min, salary_max, is_salary_negotiable,
                    tech_stack, domain_knowledge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                raw_id,
                url,
                analysis.standardized_title,
                analysis.job_level,
                int(analysis.is_internship),
                json.dumps(analysis.cities, ensure_ascii=False),
                analysis.min_years_experience,
                analysis.min_gpa,
                analysis.english_requirement,
                analysis.salary_min,
                analysis.salary_max,
                int(analysis.is_salary_negotiable),
                json.dumps(analysis.tech_stack, ensure_ascii=False),
                json.dumps(analysis.domain_knowledge, ensure_ascii=False)
            ))

            # Mark as processed in raw_jobs
            cursor.execute('''
                UPDATE raw_jobs SET is_processed = 1 WHERE id = ?
            ''', (raw_id,))

            self.conn.commit()
            logger.info(f"Saved analysis for: {analysis.standardized_title}")
            return True
        except Exception as e:
            logger.error(f"DB Error save_clean_job: {e}")
            self.conn.rollback() # Good practice to rollback on error
            return False
        
    def fetch_unparsed_jobs(self) -> List[Dict[str, Any]]:
        self.connect()
        cursor = self.conn.cursor()
        cursor.execute('''SELECT * FROM raw_jobs WHERE is_processed = 0''')

        unparsed_jobs = []
        for row in cursor.fetchall():
            unparsed_jobs.append(row)

        return unparsed_jobs

    
    @staticmethod
    def _sanitize_text(s: Any) -> Optional[str]:
        """Helper to clean text."""
        if s is None:
            return None
        if not isinstance(s, str):
            s = str(s)
        s = s.replace("\x00", "").strip()
        return " ".join(s.split()) if s else ""

if __name__ == '__main__':
    # Usage Example
    db = JobDatabase()
    db.init_db()