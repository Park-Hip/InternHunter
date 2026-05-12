"""
Thin CLI wrapper around the Prefect ingestion flow.

This is the ONLY entry point for running the pipeline.
All orchestration logic lives in src/flows/ingestion_flow.py.
"""
import asyncio
import argparse
from src.flows.ingestion_flow import job_ingestion_flow


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="InternHunter ETL Pipeline")
    parser.add_argument("--limit", type=int, default=10, help="Number of jobs to process in the LLM phase")
    args = parser.parse_args()

    asyncio.run(job_ingestion_flow(limit=args.limit))
