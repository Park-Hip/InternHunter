import sqlite3
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from src.settings.settings import DATA_DIR
from src.database.database import JobDatabase

# Setup basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

def migrate():
    db_path = (DATA_DIR / "db" / "jobs.db").resolve()
    if not db_path.exists():
        logger.error(f"Database not found at {db_path}")
        return

    # 1. Backup existing DB
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.parent / f"jobs_backup_{timestamp}.db"
    shutil.move(str(db_path), str(backup_path))
    logger.info(f"Backed up existing database to {backup_path}")

    # 2. Initialize new DB (with new schema)
    new_db = JobDatabase(db_path)
    new_db.init_db()
    logger.info("Initialized new database with updated schema")

    # 3. Connect to Backup DB to read old data
    old_conn = sqlite3.connect(str(backup_path))
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()

    # 4. Migrate Raw Jobs
    logger.info("Migrating raw_jobs...")
    old_cursor.execute("SELECT * FROM raw_jobs")
    raw_jobs = old_cursor.fetchall()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    for job in raw_jobs:
        # Check if columns exist in old db, handle missing gracefully if needed
        # Old schema: url, title, company, full_json_dump, scraped_at, source, is_processed
        # New schema: id, url, title, full_json_dump, scraped_at, source, is_processed (plus company? let's check db definition)
        # database.py define: url, title, company, full_json_dump, scraped_at, source, is_processed
        
        try:
            cursor.execute('''
                INSERT INTO raw_jobs (url, title, company, full_json_dump, scraped_at, source, is_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                job['url'],
                job['title'],
                job['company'],
                job['full_json_dump'],
                job['scraped_at'],
                job['source'],
                job['is_processed']
            ))
        except Exception as e:
            logger.error(f"Failed to migrate raw job {job['url']}: {e}")

    conn.commit()
    logger.info(f"Migrated {len(raw_jobs)} raw jobs.")

    # 5. Migrate Clean Jobs
    logger.info("Migrating clean_jobs...")
    # Check if clean_jobs exists in old db
    try:
        old_cursor.execute("SELECT * FROM clean_jobs")
        clean_jobs = old_cursor.fetchall()
    except sqlite3.OperationalError:
        logger.warning("Old database does not have 'clean_jobs' table. Skipping clean jobs migration.")
        clean_jobs = []

    migrated_clean_count = 0
    for job in clean_jobs:
        url = job['url']
        
        # Find new ID for this URL
        cursor.execute("SELECT id FROM raw_jobs WHERE url = ?", (url,))
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"Could not find new ID for clean job URL: {url}. Skipping.")
            continue
            
        new_id = row[0]
        
        try:
            # Old schema keys from db_schema.txt:
            # url, standardized_title, job_level, is_internship, cities, min_years_experience, 
            # min_gpa, english_requirement, salary_min, salary_max, is_salary_negotiable, 
            # tech_stack, domain_knowledge
            
            cursor.execute('''
                INSERT INTO clean_jobs (
                    id, url, standardized_title, job_level, is_internship, cities,
                    min_years_experience, min_gpa, english_requirement, salary_min, salary_max,
                    is_salary_negotiable, tech_stack, domain_knowledge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                new_id,
                url,
                job['standardized_title'],
                job['job_level'],
                job['is_internship'],
                job['cities'],
                job['min_years_experience'],
                job['min_gpa'],
                job['english_requirement'],
                job['salary_min'],
                job['salary_max'],
                job['is_salary_negotiable'],
                job['tech_stack'],
                job['domain_knowledge']
            ))
            migrated_clean_count += 1
        except Exception as e:
            logger.error(f"Failed to migrate clean job {url}: {e}")

    conn.commit()
    logger.info(f"Migrated {migrated_clean_count} clean jobs.")
    
    conn.close()
    old_conn.close()
    logger.info("Migration complete.")

if __name__ == "__main__":
    migrate()
