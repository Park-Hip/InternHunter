import importlib.util


def test_supported_entrypoints_import():
    from src.internhunter.orchestration.flows import run_production_pipeline
    from src.internhunter.orchestration.ingestion_flow import job_ingestion_flow
    from src.run_pipeline import run_full_pipeline
    from src.scripts.run_production_v2 import main as run_production_v2_main

    assert callable(run_full_pipeline)
    assert callable(job_ingestion_flow)
    assert callable(run_production_pipeline)
    assert callable(run_production_v2_main)


def test_removed_cli_entrypoints_are_absent():
    assert importlib.util.find_spec("src.main") is None
    assert importlib.util.find_spec("src.internhunter.orchestration.cli") is None
