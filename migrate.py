import sqlite3
from src.settings.settings import DATA_DIR

# ==========================================
# ⚠️ CONFIGURATION: PUT YOUR GOOD BACKUP NAME HERE
# Check src/data/db/ and copy the name of the largest backup file
# Example: "jobs_backup_20260205_112102.db"
SOURCE_BACKUP_FILENAME = "jobs_backup_20260205_112102.db" 
# ==========================================

def migrate():
    # 1. DEFINE PATHS
    # We read FROM the specific backup you chose
    source_path = (DATA_DIR / "db" / SOURCE_BACKUP_FILENAME).resolve()
    
    # We write TO the main jobs.db file
    dest_path = (DATA_DIR / "db" / "jobs.db").resolve()

    if not source_path.exists():
        print(f"❌ ERROR: Could not find backup file: {SOURCE_BACKUP_FILENAME}")
        print("   Please check the filename in the script.")
        return

    print(f"📖 Reading from source: {source_path.name}")
    print(f"✍️  Writing to destination: {dest_path.name}")

    # 2. CONNECT TO SOURCE (OLD DATA)
    old_conn = sqlite3.connect(source_path)
    old_conn.row_factory = sqlite3.Row 
    old_cursor = old_conn.cursor()

    # 3. RESET DESTINATION DB
    # We delete the current broken jobs.db to start fresh
    if dest_path.exists():
        try:
            dest_path.unlink()
            print("🗑️  Deleted old broken jobs.db")
        except PermissionError:
            print("❌ ERROR: Close DB Browser or VS Code SQLite viewer!")
            return

    # 4. SETUP NEW CONNECTION
    new_conn = sqlite3.connect(dest_path) 
    new_conn.row_factory = sqlite3.Row
    new_cursor = new_conn.cursor()

    # 5. CREATE TABLES MANUALLY
    print("🔨 Creating table structures...")
    
    new_cursor.execute("""
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
    """)

    new_cursor.execute("""
    CREATE TABLE IF NOT EXISTS clean_jobs (
        id INTEGER PRIMARY KEY,
        url TEXT UNIQUE,
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
    """)
    new_conn.commit()

    print("🚀 Start restoring & migrating data...")

    try:
        # --- MIGRATE RAW JOBS ---
        old_cursor.execute("SELECT * FROM raw_jobs")
        raw_jobs = old_cursor.fetchall()

        print(f"   Moving {len(raw_jobs)} raw jobs...")
        for row in raw_jobs:
            new_cursor.execute("""
            INSERT INTO raw_jobs (url, title, company, full_json_dump, scraped_at, source, is_processed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                row["url"], row['title'], row['company'], 
                row['full_json_dump'], row['scraped_at'], 
                row["source"], row['is_processed']
            ))

        # --- MIGRATE CLEAN JOBS ---
        old_cursor.execute("SELECT * FROM clean_jobs")
        clean_jobs = old_cursor.fetchall()

        print(f"   Moving {len(clean_jobs)} clean jobs...")
        migrated_count = 0

        for row in clean_jobs:
            url = row['url']
            
            # Find the new ID for this URL
            new_cursor.execute("SELECT id FROM raw_jobs WHERE url = ?", (url,))
            result = new_cursor.fetchone()

            if result:
                new_id = result['id'] 

                new_cursor.execute("""
                INSERT INTO clean_jobs (
                    id, url, standardized_title, job_level, is_internship, cities, 
                    min_years_experience, min_gpa, english_requirement, 
                    salary_min, salary_max, is_salary_negotiable, 
                    tech_stack, domain_knowledge
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_id, row['url'], row['standardized_title'], row['job_level'], row['is_internship'], row['cities'],
                    row['min_years_experience'], row['min_gpa'], row['english_requirement'],
                    row['salary_min'], row['salary_max'], row['is_salary_negotiable'],
                    row['tech_stack'], row['domain_knowledge']
                ))
                migrated_count += 1

        new_conn.commit()
        print(f"✅ Success! Restored & Migrated {migrated_count} clean jobs.")

    except Exception as e:
        print(f"❌ FATAL ERROR: {e}")
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    migrate()