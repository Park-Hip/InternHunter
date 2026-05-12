from src.internhunter.orchestration.flows import job_ingestion_flow, run_production_pipeline
from src.internhunter.orchestration.ingestion_flow import job_ingestion_flow as canonical_ingestion_flow
from src.internhunter.orchestration.tasks import (
    acquire_job_task,
    fetch_job_links_task,
    process_pending_jobs_task,
)


def test_orchestration_imports_resolve():
    from src.flows.ingestion_flow import job_ingestion_flow as legacy_ingestion_flow
    from src.infrastructure.prefect.flows import run_production_pipeline as legacy_production_flow
    from src.infrastructure.prefect.tasks import (
        acquire_job_task as legacy_acquire_job_task,
        fetch_job_links_task as legacy_fetch_job_links_task,
        process_pending_jobs_task as legacy_process_pending_jobs_task,
    )

    assert canonical_ingestion_flow is job_ingestion_flow
    assert legacy_ingestion_flow is canonical_ingestion_flow
    assert legacy_production_flow is run_production_pipeline
    assert legacy_fetch_job_links_task is fetch_job_links_task
    assert legacy_acquire_job_task is acquire_job_task
    assert legacy_process_pending_jobs_task is process_pending_jobs_task
