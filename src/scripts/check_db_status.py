from src.infrastructure.db.repositories.etl import ETLRepository
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.db.models import AuditJobDB, RawJobDB, CleanJobDB

def check():
    repo = ETLRepository()
    session = SessionLocal()
    
    print(f"Total Raw Jobs: {repo.get_raw_jobs_count()}")
    print(f"Audit Entries (DLQ): {session.query(AuditJobDB).count()}")
    print(f"Pending Raw Jobs: {session.query(RawJobDB).filter(RawJobDB.status == 'pending').count()}")
    print(f"Completed Raw Jobs: {session.query(RawJobDB).filter(RawJobDB.status == 'completed').count()}")
    print(f"Failed Raw Jobs: {session.query(RawJobDB).filter(RawJobDB.status == 'failed').count()}")
    print(f"Total Clean Jobs: {session.query(CleanJobDB).count()}")
    
    # Check some audit entries
    if session.query(AuditJobDB).count() > 0:
        print("\nLatest Audit Entries:")
        for entry in session.query(AuditJobDB).order_by(AuditJobDB.created_at.desc()).limit(3):
            print(f"- {entry.url}: {entry.error_type} -> {entry.error_message}")

if __name__ == "__main__":
    check()
