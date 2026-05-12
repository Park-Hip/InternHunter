import asyncio
import uuid

from prefect import flow, serve

from src.internhunter.common.logging import get_logger, bind_context
from src.internhunter.config.settings import settings
from src.internhunter.orchestration.ingestion_flow import job_ingestion_flow
from src.internhunter.orchestration.tasks import fetch_job_links_task, acquire_job_task, process_pending_jobs_task

logger = get_logger(__name__)


@flow(name="Production Job Pipeline")
async def run_production_pipeline(url: str):
    run_id = str(uuid.uuid4())[:8]
    bind_context(run_id=run_id)

    logger.info("Starting production pipeline", url=url, run_id=run_id)

    new_links = await fetch_job_links_task(run_id, url)

    if not new_links:
        logger.info("No new links found, moving to processing existing pending jobs")
    else:
        tasks = [acquire_job_task(link["url"], run_id) for link in new_links]
        await asyncio.gather(*tasks)

    await process_pending_jobs_task(limit=50)

    logger.info("Production pipeline completed", run_id=run_id)


if __name__ == "__main__":
    ds_deploy = run_production_pipeline.to_deployment(
        name="ds-scraper-v2",
        cron="0 3 * * *",
        parameters={"url": settings.DS_URL},
    )

    ai_deploy = run_production_pipeline.to_deployment(
        name="ai-scraper-v2",
        cron="0 4 * * *",
        parameters={"url": settings.AIE_URL},
    )

    serve(ds_deploy, ai_deploy)


__all__ = ["job_ingestion_flow", "run_production_pipeline"]
