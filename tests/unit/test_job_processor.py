import pytest
from src.services.job_processor.job_processor import JobProcessor
from src.infrastructure.db.repositories.etl import ETLRepository
from src.infrastructure.db.models import RawJobDB

@pytest.fixture
def repo(test_db_session):
    return ETLRepository()

@pytest.fixture
def processor(mock_gemini_client):
    # The processor uses the mocked Gemini client automatically 
    # thanks to the monkeypatching in the fixture.
    return JobProcessor()

def test_process_jobs_success(test_db_session, repo, processor, mocker):
    # 1. Setup: Insert a pending raw job
    repo.save_raw_job({
        "url": "https://example.com/job/process-me",
        "title": "Raw Title",
        "raw_markdown": "This is a dummy job description containing over 300 characters. " * 10, # Pass heuristic
        "status": "pending"
    })
    
    # Mock the Embedder since we don't want to make real API calls for embeddings
    mocker.patch("src.services.job_processor.embedder.Embedder.generate_embedding", return_value=[0.1]*768)
    
    # Mock validator to pass
    mocker.patch("src.services.job_processor.validator.JobValidator.is_valid", return_value=(True, ""))

    # 2. Act: Run processing
    success_count, fail_count = processor.process_jobs(limit=10)
    
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

def test_process_jobs_validation_fails(test_db_session, repo, processor, mocker):
    # 1. Setup
    repo.save_raw_job({
        "url": "https://example.com/job/bad",
        "raw_markdown": "Too short",
        "status": "pending"
    })
    
    # Force validator to fail
    mocker.patch("src.services.job_processor.validator.JobValidator.is_valid", return_value=(False, "Heuristic Failed"))
    
    # 2. Act
    success, fail = processor.process_jobs(limit=10)
    
    # 3. Assert
    assert success == 0
    assert fail == 1 # Validation fails count as processing errors (status='failed')
    
    # Wait, the processor code marks validation failures as 'invalid'. Let's check.
    # Ah, if we look at job_processor.py:
    # if not is_valid: ... repo.update_job_status(job.id, "invalid") -> wait, the actual code says "failed". Let's check status.
    raw_job = test_db_session.query(RawJobDB).filter_by(url="https://example.com/job/bad").first()
    assert raw_job.status == "failed"
