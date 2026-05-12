import os
import pytest
from prefect.testing.utilities import prefect_test_harness
from src.flows.ingestion_flow import job_ingestion_flow
from src.infrastructure.db.models import PipelineRunDB

pytestmark = [
    pytest.mark.integration_db,
    pytest.mark.skipif(
        os.getenv("RUN_DB_TESTS") != "1",
        reason="This integration test requires a live configured PostgreSQL database.",
    ),
]

@pytest.fixture(autouse=True, scope="session")
def prefect_test_fixture():
    with prefect_test_harness():
        yield

@pytest.mark.asyncio
async def test_job_ingestion_flow(test_db_session, mocker, mock_gemini_client):
    """Integration test for the entire ETL pipeline."""
    
    # 1. Setup Mocking for the Crawler
    # We don't want to actually launch Playwright during our integration test.
    
    # Mock fetch_job_links to return 2 dummy links
    mocker.patch(
        "src.services.crawler.crawl.Crawler.fetch_job_links",
        return_value=[
            {"url": "https://example.com/job/flow1", "title": "Flow Job 1"},
            {"url": "https://example.com/job/flow2", "title": "Flow Job 2"}
        ]
    )
    
    # Mock crawl_jobs to just insert the jobs directly into the database
    # simulating a successful crawl.
    async def mock_crawl_jobs(links, run_id):
        from src.infrastructure.db.repositories.etl import ETLRepository
        repo = ETLRepository()
        for link in links:
            repo.save_raw_job({
                "url": link["url"],
                "title": link["title"],
                "raw_markdown": "Integration test job content. " * 20,
                "status": "pending"
            })
            
    mocker.patch("src.services.crawler.crawl.Crawler.crawl_jobs", side_effect=mock_crawl_jobs)
    
    # Mock embedder and validator
    mocker.patch("src.services.job_processor.embedder.Embedder.generate_embedding", return_value=[0.5]*768)
    mocker.patch("src.services.job_processor.validator.JobValidator.is_valid", return_value=(True, ""))

    # 2. Act: Execute the Prefect Flow
    # The flow will fetch the 2 mocked links, crawl them (via our mock insert), 
    # process them (using the mock_gemini_client), and save telemetry.
    await job_ingestion_flow(limit=10)
    
    # 3. Assert
    # Verify that the Pipeline_Runs table registered the 2 acquired and 2 processed jobs.
    pipeline_run = test_db_session.query(PipelineRunDB).order_by(PipelineRunDB.timestamp.desc()).first()
    
    assert pipeline_run is not None
    assert pipeline_run.jobs_acquired == 2
    assert pipeline_run.jobs_processed == 2
    assert pipeline_run.jobs_failed == 0
    assert pipeline_run.status == "completed"
