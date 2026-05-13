import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.internhunter.extraction.job_processor import JobProcessor, build_validation_text
from src.infrastructure.db.repositories.etl import ETLRepository
from src.infrastructure.db.models import RawJobDB, AuditJobDB
from src.core.models import ProcessedJob
from src.services.job_processor.validator import JobValidator


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "topcv"

@pytest.fixture
def repo(test_db_session):
    return ETLRepository()

@pytest.fixture
def processor(mock_gemini_client):
    # The processor uses the mocked Gemini client automatically 
    # thanks to the monkeypatching in the fixture.
    return JobProcessor()


def load_processed_job_fixture(name: str) -> ProcessedJob:
    payload = json.loads((FIXTURE_DIR / f"{name}.extracted.json").read_text(encoding="utf-8"))
    return ProcessedJob(**payload)


def get_latest_audit_row(test_db_session):
    return test_db_session.query(AuditJobDB).order_by(AuditJobDB.id.desc()).first()


def test_build_validation_text_includes_css_success_fields():
    job = SimpleNamespace(
        title="Data Scientist",
        company="TopCV",
        location="Hanoi",
        raw_markdown=None,
        full_json_dump={
            "title": "Data Scientist",
            "company": "TopCV",
            "location": "Hanoi",
            "info": "This is a detailed job info section with responsibilities and requirements.",
            "metadata": {"blocked_reason": "blocked_or_empty_content"},
        },
    )

    text = build_validation_text(job)

    assert "Data Scientist" in text
    assert "TopCV" in text
    assert "Hanoi" in text
    assert "detailed job info section" in text
    assert "blocked_or_empty_content" not in text


def test_build_validation_text_uses_raw_markdown_for_raw_fallback():
    job = SimpleNamespace(
        title="Unknown (RAW)",
        company="Unknown (RAW)",
        location="Unknown",
        raw_markdown="This is a raw markdown job description with enough detail to validate.",
        full_json_dump={
            "error": "CSS extraction failed",
            "is_blocked": False,
            "blocked_reason": "empty_or_unparseable_css_content",
        },
    )

    text = build_validation_text(job)

    assert "This is a raw markdown job description" in text
    assert "Unknown (RAW)" in text
    assert "empty_or_unparseable_css_content" not in text


def test_build_validation_text_ignores_blocked_metadata_only_payload():
    job = SimpleNamespace(
        title=None,
        company=None,
        location=None,
        raw_markdown=None,
        full_json_dump={
            "error": "CSS extraction failed",
            "is_blocked": True,
            "blocked_reason": "blocked_or_empty_content",
        },
    )

    text = build_validation_text(job)

    assert text == ""

@pytest.mark.asyncio
async def test_process_jobs_success(test_db_session, repo, processor, mocker):
    # 1. Setup: Insert a pending raw job
    repo.save_raw_job({
        "url": "https://example.com/job/process-me",
        "title": "Raw Title",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10, # Pass heuristic
        "status": "pending"
    })
    
    # Mock the Embedder since we don't want to make real API calls for embeddings
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1]*768)
    
    # Mock validator to pass
    mocker.patch("src.internhunter.extraction.validator.JobValidator.is_valid", return_value=(True, ""))

    # Mock the LLM routing/extraction step so this stays a unit test.
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        return_value=ProcessedJob(
            standardized_title="Software Engineer Test",
            job_level="Mid",
            is_internship=False,
            cities=["Hanoi"],
            experience=2.0,
            min_gpa=None,
            english_requirement=None,
            salary_min=None,
            salary_max=None,
            currency="VND",
            is_salary_negotiable=False,
            tech_stack=["Python", "FastAPI"],
            technical_competencies=["Build APIs"],
            domain_knowledge=["Web Development"],
            description="A realistic cleaned job description for testing.",
            requirement="Python, APIs, testing",
            benefit="Flexible work",
        ),
    )

    # 2. Act: Run processing
    success_count, fail_count = await processor.process_jobs(limit=10)
    
    # 3. Assert
    assert success_count == 1
    assert fail_count == 0
    
    # Verify the job status was updated
    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/process-me").first()
    assert raw_job.status == "completed"
    
    # Verify the clean job was created and mapped correctly from the LLM Mock
    clean_job = raw_job.clean_job
    assert clean_job is not None
    assert clean_job.standardized_title == "Software Engineer Test"
    assert clean_job.job_level == "Mid"
    assert "Python" in clean_job.tech_stack


@pytest.mark.asyncio
async def test_process_jobs_default_mode_uses_llm_validation(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/default-validation",
        "title": "Data Scientist",
        "company": "TopCV",
        "location": "Hanoi",
        "full_json_dump": {
            "title": "Data Scientist",
            "company": "TopCV",
            "location": "Hanoi",
            "info": "This job description contains enough detail and job-like keywords to pass heuristics.",
            "requirement": "Python, SQL",
            "benefit": "Flexible work",
        },
        "status": "pending",
    })

    llm_validate = mocker.patch.object(JobValidator, "validate_with_llm", return_value=(True, "LLM ok"))
    mocker.patch.object(JobValidator, "heuristic_check", return_value=True)
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        return_value=ProcessedJob(
            standardized_title="Software Engineer Test",
            job_level="Mid",
            is_internship=False,
            cities=["Hanoi"],
            experience=2.0,
            min_gpa=None,
            english_requirement=None,
            salary_min=None,
            salary_max=None,
            currency="VND",
            is_salary_negotiable=False,
            tech_stack=["Python", "FastAPI"],
            technical_competencies=["Build APIs"],
            domain_knowledge=["Web Development"],
            description="A realistic cleaned job description for testing.",
            requirement="Python, APIs, testing",
            benefit="Flexible work",
        ),
    )
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1] * 768)

    success_count, fail_count = await processor.process_jobs(limit=10)

    assert llm_validate.called
    assert success_count == 1
    assert fail_count == 0


@pytest.mark.asyncio
async def test_process_jobs_skip_llm_validation_bypasses_llm_validation(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/skip-validation",
        "title": "Data Scientist",
        "company": "TopCV",
        "location": "Hanoi",
        "full_json_dump": {
            "title": "Data Scientist",
            "company": "TopCV",
            "location": "Hanoi",
            "info": "This job description contains enough detail and job-like keywords to pass heuristics.",
            "requirement": "Python, SQL",
            "benefit": "Flexible work",
        },
        "status": "pending",
    })

    mocker.patch.object(JobValidator, "heuristic_check", return_value=True)
    mocker.patch.object(JobValidator, "validate_with_llm", side_effect=AssertionError("LLM validation should be skipped"))
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        return_value=ProcessedJob(
            standardized_title="Software Engineer Test",
            job_level="Mid",
            is_internship=False,
            cities=["Hanoi"],
            experience=2.0,
            min_gpa=None,
            english_requirement=None,
            salary_min=None,
            salary_max=None,
            currency="VND",
            is_salary_negotiable=False,
            tech_stack=["Python", "FastAPI"],
            technical_competencies=["Build APIs"],
            domain_knowledge=["Web Development"],
            description="A realistic cleaned job description for testing.",
            requirement="Python, APIs, testing",
            benefit="Flexible work",
        ),
    )
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1] * 768)

    success_count, fail_count = await processor.process_jobs(limit=10, skip_llm_validation=True)

    assert success_count == 1
    assert fail_count == 0


@pytest.mark.asyncio
async def test_process_jobs_skip_llm_validation_still_fails_heuristics(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/skip-validation-fail",
        "title": "Short",
        "company": "Tiny Co",
        "location": "VN",
        "raw_markdown": "Too short",
        "status": "pending",
    })

    mocker.patch.object(JobValidator, "heuristic_check", return_value=False)
    mocker.patch.object(JobValidator, "validate_with_llm", side_effect=AssertionError("LLM validation should not be called on heuristic failure"))

    success_count, fail_count = await processor.process_jobs(limit=10, skip_llm_validation=True)

    assert success_count == 0
    assert fail_count == 1

    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/skip-validation-fail").first()
    assert raw_job.status == "failed"

    audit_row = get_latest_audit_row(test_db_session)
    assert audit_row is not None
    assert audit_row.error_type == "VALIDATION_FAILED"


@pytest.mark.asyncio
async def test_process_jobs_saves_fixture_backed_processed_job(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/fixture-backed",
        "title": "Raw Title",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10,
        "status": "pending",
    })

    structured_fixture = load_processed_job_fixture("normal_job")

    mocker.patch("src.internhunter.extraction.validator.JobValidator.is_valid", return_value=(True, ""))
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        return_value=structured_fixture,
    )
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1] * 768)

    success_count, fail_count = await processor.process_jobs(limit=10)

    assert success_count == 1
    assert fail_count == 0

    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/fixture-backed").first()
    assert raw_job.status == "completed"

    clean_job = raw_job.clean_job
    assert clean_job is not None
    assert clean_job.standardized_title == structured_fixture.standardized_title
    assert clean_job.description == structured_fixture.description
    assert list(clean_job.cities) == structured_fixture.cities
    assert list(clean_job.tech_stack) == structured_fixture.tech_stack
    assert list(clean_job.domain_knowledge) == structured_fixture.domain_knowledge

@pytest.mark.asyncio
async def test_process_jobs_validation_fails(test_db_session, repo, processor, mocker):
    # 1. Setup
    repo.save_raw_job({
        "url": "https://example.com/job/bad",
        "raw_markdown": "Too short",
        "status": "pending"
    })
    
    # Force validator to fail
    validator_reason = "Heuristic check failed: text too short or lacks job keywords."
    mocker.patch("src.internhunter.extraction.validator.JobValidator.is_valid", return_value=(False, validator_reason))
    
    # 2. Act
    success, fail = await processor.process_jobs(limit=10)
    
    # 3. Assert
    assert success == 0
    assert fail == 1 # Validation fails count as processing errors (status='failed')
    
    # Wait, the processor code marks validation failures as 'invalid'. Let's check.
    # Ah, if we look at job_processor.py:
    # if not is_valid: ... repo.update_job_status(job.id, "invalid") -> wait, the actual code says "failed". Let's check status.
    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/bad").first()
    assert raw_job.status == "failed"

    audit_row = get_latest_audit_row(test_db_session)
    assert audit_row is not None
    assert audit_row.error_type == "VALIDATION_FAILED"
    assert validator_reason in audit_row.error_message


@pytest.mark.asyncio
async def test_process_jobs_llm_incomplete_failure_is_audited(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/llm-incomplete",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10,
        "status": "pending",
    })

    mocker.patch("src.internhunter.extraction.validator.JobValidator.is_valid", return_value=(True, ""))
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        return_value=ProcessedJob(
            standardized_title="",
            job_level="Mid",
            is_internship=False,
            cities=["Hanoi"],
            experience=2.0,
            min_gpa=None,
            english_requirement=None,
            salary_min=None,
            salary_max=None,
            currency="VND",
            is_salary_negotiable=False,
            tech_stack=["Python"],
            technical_competencies=["Build APIs"],
            domain_knowledge=["Web Development"],
            description="",
            requirement="Python, APIs, testing",
            benefit="Flexible work",
        ),
    )
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1] * 768)

    success, fail = await processor.process_jobs(limit=10)

    assert success == 0
    assert fail == 1

    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/llm-incomplete").first()
    assert raw_job.status == "failed"

    audit_row = get_latest_audit_row(test_db_session)
    assert audit_row is not None
    assert audit_row.error_type == "LLM_INCOMPLETE"
    assert "Missing critical fields (title/description) in LLM output" in audit_row.error_message


@pytest.mark.asyncio
async def test_process_jobs_prioritizes_refreshed_current_run_jobs(test_db_session, repo, processor, mocker):
    repo.save_raw_job({
        "url": "https://example.com/job/older-pending-process",
        "title": "Older Pending Process",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10,
        "status": "pending",
    })
    repo.save_raw_job({
        "url": "https://example.com/job/current-run-process",
        "title": "Current Run Process",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10,
        "status": "pending",
    })
    repo.save_raw_job({
        "url": "https://example.com/job/current-run-process",
        "title": "Current Run Process Refreshed",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10,
        "status": "pending",
        "extraction_method": "raw",
    })

    mocker.patch("src.internhunter.extraction.validator.JobValidator.is_valid", return_value=(True, ""))
    mocker.patch(
        "src.internhunter.extraction.job_processor.llm_router.process_with_fallback",
        side_effect=lambda job: ProcessedJob(
            standardized_title=job.title,
            job_level="Mid",
            is_internship=False,
            cities=["Hanoi"],
            experience=2.0,
            min_gpa=None,
            english_requirement=None,
            salary_min=None,
            salary_max=None,
            currency="VND",
            is_salary_negotiable=False,
            tech_stack=["Python"],
            technical_competencies=["Build APIs"],
            domain_knowledge=["Web Development"],
            description=f"Processed {job.title}",
            requirement="Python, APIs, testing",
            benefit="Flexible work",
        ),
    )
    mocker.patch("src.internhunter.embeddings.embedder.Embedder.generate_embedding", return_value=[0.1] * 768)

    success_count, fail_count = await processor.process_jobs(limit=1)

    assert success_count == 1
    assert fail_count == 0

    current_run_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/current-run-process").first()
    older_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/older-pending-process").first()

    assert current_run_job.status == "completed"
    assert older_job.status == "pending"
