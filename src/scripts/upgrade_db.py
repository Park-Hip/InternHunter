import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import sqlalchemy as sa
from internhunter.config.settings import settings
from infrastructure.db.session import engine
from infrastructure.db.models import Base

def upgrade():
    print("Upgrading database...")
    
    with engine.connect() as conn:
        # 1. Add columns to raw_jobs if they don't exist
        columns_to_add = [
            ("status", "VARCHAR", "'pending'"),
            ("extraction_method", "VARCHAR", "'css'"),
            ("raw_markdown", "TEXT", "NULL"),
            ("retry_count", "INTEGER", "0")
        ]
        
        for col_name, col_type, default in columns_to_add:
            try:
                # Check if column exists
                check_query = sa.text(f"SELECT column_name FROM information_schema.columns WHERE table_name='raw_jobs' AND column_name='{col_name}'")
                exists = conn.execute(check_query).fetchone()
                
                if not exists:
                    print(f"Adding column {col_name}...")
                    conn.execute(sa.text(f"ALTER TABLE raw_jobs ADD COLUMN {col_name} {col_type} DEFAULT {default}"))
                    conn.commit()
            except Exception as e:
                print(f"Failed to add column {col_name}: {e}")

        # 2. Create audit_jobs table if it doesn't exist
        try:
            print("Creating audit_jobs table if needed...")
            Base.metadata.create_all(bind=engine)
            print("Table verification complete.")
        except Exception as e:
            print(f"Failed to create tables: {e}")

if __name__ == "__main__":
    upgrade()
