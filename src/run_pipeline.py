import asyncio
import uuid
import argparse
from src.infrastructure.logging import configure_logging, get_logger, bind_context, clear_context
from src.infrastructure.db.repository import JobRepository
from src.services.crawler.crawl import run_crawler_pipeline
from src.services.job_processor.job_processor import JobProcessor

logger = get_logger(__name__)

async def run_full_pipeline(limit: int = 10):
    """
    Orchestrates the entire ETL pipeline:
    1. Database initialization.
    2. Crawler (link fetching and detail extraction).
    3. Job Processing (LLM-based extraction and cleaning).
    """
    # Ensure logging is configured (though main.py might have already done it)
    configure_logging()
    
    run_id = str(uuid.uuid4())[:8]
    bind_context(run_id=run_id)
    
    logger.info("Starting integrated pipeline", limit=limit)
    
    try:
        # Step 1: Database Initialization
        logger.info("Phase 1: Database Initialization", status="start")
        repo = JobRepository()
        repo.create_tables()
        logger.info("Phase 1: Database Initialization", status="done")
        
        # Step 2: Crawler
        logger.info("Phase 2: Crawler", status="start")
        # run_crawler_pipeline internally handles link fetching and detail extraction
        await run_crawler_pipeline(run_id)
        logger.info("Phase 2: Crawler", status="done")
        
        # Step 3: Job Processor
        logger.info("Phase 3: Job Processor", status="start")
        processor = JobProcessor()
        processor.process_jobs(limit=limit)
        logger.info("Phase 3: Job Processor", status="done")
        
        logger.info("Integrated pipeline completed successfully")
        
    except Exception as e:
        logger.error("Integrated pipeline failed", error=str(e), exc_info=True)
        raise
    finally:
        clear_context()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Integrated Job Finder Pipeline")
    parser.add_argument("--limit", type=int, default=10, help="Number of jobs to process in the LLM phase")
    args = parser.parse_args()
    
    asyncio.run(run_full_pipeline(limit=args.limit))
