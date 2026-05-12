import os
import sys
import time
from sqlalchemy import select

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.infrastructure.db.session import SessionLocal
from src.infrastructure.db.models import CleanJobDB
from src.internhunter.embeddings.embedder import embedder
from src.internhunter.common.logging import get_logger

logger = get_logger(__name__)

def backfill_embeddings():
    """
    Iterates through CleanJobDB records with missing embeddings and populates them.
    """
    logger.info("Starting embedding backfill process...")
    
    with SessionLocal() as session:
        # 1. Fetch jobs where embedding is NULL
        stmt = select(CleanJobDB).where(CleanJobDB.embedding.is_(None))
        jobs = session.execute(stmt).scalars().all()
        
        total_jobs = len(jobs)
        logger.info(f"Found {total_jobs} jobs needing embeddings.")
        
        if total_jobs == 0:
            return

        success_count = 0
        
        for i, job in enumerate(jobs):
            try:
                # 2. Construct text representation
                # Using a rich representation for better semantic search
                technical = ", ".join(job.technical_competencies) if job.technical_competencies else ""
                text_to_embed = f"{job.standardized_title}. {job.description}. {technical}"
                
                # Truncate if too long (GenAI has limits, though usually high for embeddings)
                if len(text_to_embed) > 9000:
                    text_to_embed = text_to_embed[:9000]

                # 3. Generate embedding
                vector = embedder.generate_embedding(text_to_embed)
                
                # 4. Update job
                job.embedding = vector
                success_count += 1
                
                # Commit in batches of 10 to be safe/fast
                if success_count % 10 == 0:
                    session.commit()
                    logger.info(f"Processed {success_count}/{total_jobs} jobs...")
                
                # Slight sleep to avoid rate limits if purely sequential
                time.sleep(0.1) 

            except Exception as e:
                logger.error(f"Failed to embed job ID {job.id}: {e}")
                continue

        session.commit()
        logger.info(f"Backfill complete! Successfully embedded {success_count}/{total_jobs} jobs.")

if __name__ == "__main__":
    backfill_embeddings()
