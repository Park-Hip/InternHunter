from datetime import datetime
import json
import logging
import os
import uuid
from dotenv import load_dotenv
import time

from src.database.database import JobDatabase
from src.settings.settings import *

from src.etl.client import GeminiClient

from google import genai
from google.genai import types
import mlflow

logger = logging.getLogger(__name__)

load_dotenv()

def run():
    run_id = str(uuid.uuid4())[:8]
    logger.info("run_id=%s pipeline=start", run_id)

    db = JobDatabase()
    
    # Initialize client safely (handles missing API keys gracefully if needed, or fails fast)
    try:
        client = GeminiClient()
    except Exception as e:
        logger.critical(f"Failed to initialize GeminiClient: {e}")
        return

    unparsed_jobs = db.fetch_unparsed_jobs()
    logger.info("Found %s unparsed jobs", len(unparsed_jobs))

    success_count = 0
    fail_count = 0

    for job_row in unparsed_jobs:

        job = dict(job_row)

        job_title = job.get('title')
        job_company = job.get('company')
        job_url = job.get('url')

        try:
            full_json_dump = json.loads(job['full_json_dump'])
            result = client.generate_content(full_json_dump)
            
            logger.info("Parsing content for job %s @ %s", job_title, job_company)
            
            if db.save_clean_job(job_url, result):
                success_count += 1
            else:
                fail_count += 1
                logger.error("Failed to save job %s @ %s to database.", job_title, job_company)

        except Exception as e:
            fail_count += 1
            logger.error("Error processing job %s @ %s: %s", job_title, job_company, e)

        finally:
            time.sleep(7)

    logger.info("run_id=%s pipeline=end success=%d fail=%d", run_id, success_count, fail_count)

if __name__ == "__main__":
    log_filename = f"{LOGS_DIR}/pipeline_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s - %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(),
        ]
    )
    
    run()