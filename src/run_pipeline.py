import asyncio
import argparse
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.internhunter.orchestration.ingestion_flow import job_ingestion_flow


async def run_full_pipeline(limit: int = 10):
    """Compatibility alias for the current ingestion flow."""
    await job_ingestion_flow(limit=limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InternHunter ETL Pipeline")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of job detail pages to crawl and process in the local MVP slice",
    )
    args = parser.parse_args()

    asyncio.run(job_ingestion_flow(limit=args.limit))
