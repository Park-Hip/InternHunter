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


def test_canonical_etl_repository_refreshes_duplicate_raw_job(test_db_session):
    repo = NewETLRepository()
    first_payload = {
        "url": "https://example.com/job/storage-duplicate",
        "title": "Initial Title",
        "company": "Boundary Co",
        "location": "Remote",
        "full_json_dump": {"version": 1},
        "status": "pending",
        "retry_count": 0,
    }
    refreshed_payload = {
        "url": "https://example.com/job/storage-duplicate",
        "title": "Refreshed Title",
        "company": "Boundary Co 2",
        "location": "Hanoi",
        "full_json_dump": {"version": 2},
        "status": "pending",
        "extraction_method": "raw",
        "raw_markdown": "updated markdown",
    }

    assert repo.save_raw_job(first_payload)
    assert repo.save_raw_job(refreshed_payload)

    from src.infrastructure.db.models import RawJobDB

    saved_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/storage-duplicate").first()
    assert saved_job is not None
    assert saved_job.title == "Refreshed Title"
    assert saved_job.company == "Boundary Co 2"
    assert saved_job.location == "Hanoi"
    assert saved_job.full_json_dump == {"version": 2}
    assert saved_job.extraction_method == "raw"
    assert saved_job.raw_markdown == "updated markdown"
    assert saved_job.retry_count == 1


def test_canonical_etl_repository_filters_existing_links(test_db_session):
    repo = NewETLRepository()
    assert repo.save_raw_job(
        {
            "url": "https://example.com/job/dedup-existing",
            "title": "Existing Job",
            "company": "Boundary Co",
            "location": "Remote",
            "full_json_dump": {"foo": "bar"},
            "status": "pending",
        }
    )

    filtered = repo.filter_new_links(
        [
            {"url": "https://example.com/job/dedup-existing"},
            {"url": "https://example.com/job/dedup-new"},
        ]
    )

    assert len(filtered) == 1
    assert filtered[0]["url"] == "https://example.com/job/dedup-new"
