import argparse
import sys
from src.config.settings import settings
from src.infrastructure.logging import get_logger, configure_logging

logger = get_logger(__name__)

def main():
    # Initialize structlog
    configure_logging()
    
    parser = argparse.ArgumentParser(description="Job Finder ETL CLI (v2)")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Process (LLM) Command
    process_parser = subparsers.add_parser("process", help="Run the AI job processing pipeline (LLM extraction)")
    process_parser.add_argument("--limit", type=int, default=10, help="Number of jobs to process")

    # Crawl Command
    crawl_parser = subparsers.add_parser("crawl", help="Run the web crawler (Link fetching + detail extraction)")

    # DB Init Command
    subparsers.add_parser("init-db", help="Initialize database schema")

    # All Command
    all_parser = subparsers.add_parser("all", help="Run full integrated pipeline (Init + Crawl + Process)")
    all_parser.add_argument("--limit", type=int, default=10, help="Number of jobs to process in the LLM phase")

    # Serve Command
    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI chat server")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port")

    args = parser.parse_args()

    if args.command == "process":
        from src.services.job_processor.job_processor import run_pipeline
        logger.info("Starting AI processing pipeline", version="v2", limit=args.limit)
        run_pipeline(limit=args.limit)
    
    elif args.command == "crawl":
        import asyncio
        import uuid
        from src.services.crawler.crawl import run_crawler_pipeline
        run_id = str(uuid.uuid4())[:8]
        logger.info("Starting crawler pipeline", run_id=run_id)
        asyncio.run(run_crawler_pipeline(run_id))
    
    elif args.command == "init-db":
        from src.infrastructure.db.repository import JobRepository
        logger.info("Initializing database schema")
        repo = JobRepository()
        repo.create_tables()
        logger.info("Database initialized successfully")

    elif args.command == "all":
        import asyncio
        from src.run_pipeline import run_full_pipeline
        logger.info("Starting full integrated pipeline")
        asyncio.run(run_full_pipeline(limit=args.limit))
    
    elif args.command == "serve":
        import uvicorn
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from src.infrastructure.api.routes.chat_routes import router as chat_router
        
        app = FastAPI(title="Job Finder API", version="1.0.0")
        
        # Add CORS middleware to allow frontend requests
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        app.include_router(chat_router)
        logger.info("Starting API server", host=args.host, port=args.port)
        uvicorn.run(app, host=args.host, port=args.port)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
