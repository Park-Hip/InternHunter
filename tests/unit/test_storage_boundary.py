from src.internhunter.storage.models import (
    Base as NewBase,
    RawJobDB as NewRawJobDB,
    AuditJobDB as NewAuditJobDB,
    CleanJobDB as NewCleanJobDB,
    PipelineRunDB as NewPipelineRunDB,
)
from src.internhunter.storage.repositories.etl import ETLRepository as NewETLRepository
from src.internhunter.storage.repositories.search import SearchRepository as NewSearchRepository
from src.internhunter.storage.repositories.chat import ChatRepository as NewChatRepository
from src.internhunter.storage.session import SessionLocal as NewSessionLocal, engine as NewEngine


def test_storage_model_and_session_imports():
    from src.infrastructure.db.models import (
        Base as LegacyBase,
        RawJobDB as LegacyRawJobDB,
        AuditJobDB as LegacyAuditJobDB,
        CleanJobDB as LegacyCleanJobDB,
        PipelineRunDB as LegacyPipelineRunDB,
    )
    from src.infrastructure.db.session import SessionLocal as LegacySessionLocal, engine as LegacyEngine

    assert NewBase is LegacyBase
    assert NewRawJobDB is LegacyRawJobDB
    assert NewAuditJobDB is LegacyAuditJobDB
    assert NewCleanJobDB is LegacyCleanJobDB
    assert NewPipelineRunDB is LegacyPipelineRunDB
    assert NewEngine is LegacyEngine
    assert NewSessionLocal is LegacySessionLocal


def test_storage_repository_imports():
    from src.infrastructure.db.repositories.etl import ETLRepository as LegacyETLRepository
    from src.infrastructure.db.repositories.search import SearchRepository as LegacySearchRepository
    from src.infrastructure.db.repositories.chat import ChatRepository as LegacyChatRepository

    assert NewETLRepository is LegacyETLRepository
    assert NewSearchRepository is LegacySearchRepository
    assert NewChatRepository is LegacyChatRepository


def test_canonical_etl_repository_writes_raw_job(test_db_session):
    repo = NewETLRepository()
    assert repo.save_raw_job(
        {
            "url": "https://example.com/job/storage-boundary",
            "title": "Storage Boundary Job",
            "company": "Boundary Co",
            "location": "Remote",
            "full_json_dump": {"foo": "bar"},
            "status": "pending",
        }
    )

    from src.infrastructure.db.models import RawJobDB

    saved_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/storage-boundary").first()
    assert saved_job is not None
    assert saved_job.title == "Storage Boundary Job"
    assert saved_job.status == "pending"

