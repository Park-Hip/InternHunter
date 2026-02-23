import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, make_transient
from src.config import settings
from src.infrastructure.db.models import Base, RawJobDB, CleanJobDB

def run():
    print("Starting migration...")
    
    # 1. Setup Connections
    old_db_url = "sqlite:///./job-finder.db"
    
    # Handle possible SecretStr for new DB
    if hasattr(settings.DB_URL, 'get_secret_value'):
        new_db_url = settings.DB_URL.get_secret_value()
    else:
        new_db_url = settings.DB_URL

    print(f"Old DB: {old_db_url}")
    print(f"New DB: {new_db_url}")

    old_engine = create_engine(
        old_db_url,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
    )
    new_engine = create_engine(
        new_db_url,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
    )

    # 2. Create Tables in New DB
    print("Creating tables in new database...")
    Base.metadata.create_all(new_engine)

    # 3. Setup Sessions
    OldSession = sessionmaker(bind=old_engine)
    NewSession = sessionmaker(bind=new_engine)

    try:
        with OldSession() as old_session:
            # 4. Migrate Raw Jobs
            print("Fetching raw jobs from SQLite...")
            raw_jobs = old_session.execute(select(RawJobDB)).scalars().all()
            print(f"Found {len(raw_jobs)} raw jobs.")

            with NewSession() as new_session:
                count = 0
                for job in raw_jobs:
                    # Detach from old session and remove identity key to allow insert
                    make_transient(job)
                    new_session.merge(job)
                    count += 1
                    
                    if count % 100 == 0:
                        new_session.commit()
                        print(f"Migrated {count} raw jobs...")
                
                new_session.commit()
                print("Raw jobs migration complete.")

            # 5. Migrate Clean Jobs (if needed)
            # You might want to enable this if you have data in clean_jobs
            print("Fetching clean jobs from SQLite...")
            clean_jobs = old_session.execute(select(CleanJobDB)).scalars().all()
            print(f"Found {len(clean_jobs)} clean jobs.")
            
            with NewSession() as new_session:
                count = 0
                for job in clean_jobs:
                    make_transient(job)
                    new_session.merge(job)
                    count += 1
                new_session.commit()
                print("Clean jobs migration complete.")

    except Exception as e:
        print(f"Migration failed: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    run()
