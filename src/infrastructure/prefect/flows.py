import uuid
import asyncio
from prefect import flow, serve
from src.infrastructure.logging import get_logger, bind_context
from src.infrastructure.prefect.tasks import fetch_job_links_task, acquire_job_task, process_pending_jobs_task
from src.config.settings import settings

logger = get_logger(__name__)

@flow(name="Production Job Pipeline")
async def run_production_pipeline(url: str):
    run_id = str(uuid.uuid4())[:8]
    bind_context(run_id=run_id)
    
    logger.info("Starting production pipeline", url=url, run_id=run_id)
    
    # 1. Fetch Links
    new_links = await fetch_job_links_task(run_id, url)
    
    if not new_links:
        logger.info("No new links found, moving to processing existing pending jobs")
    else:
        # 2. Acquire (Scrape/Raw Fallback)
        # We run these concurrently but with some natural delay in the task itself
        # to avoid hitting rate limits too hard.
        tasks = [acquire_job_task(link["url"], run_id) for link in new_links]
        await asyncio.gather(*tasks)

    # 3. Process (Validate -> Transform -> Load)
    # This task handles the hybrid guardrail and strict quality gate
    await process_pending_jobs_task(limit=50)
    
    logger.info("Production pipeline completed", run_id=run_id)

if __name__ == "__main__":
    # Define deployments
    ds_deploy = run_production_pipeline.to_deployment(
        name="ds-scraper-v2",
        cron="0 3 * * *", 
        parameters={"url": settings.DS_URL}
    )

    ai_deploy = run_production_pipeline.to_deployment(
        name="ai-scraper-v2",
        cron="0 4 * * *", 
        parameters={"url": settings.AIE_URL}
    )

    # Serve deployments
    serve(ds_deploy, ai_deploy)
