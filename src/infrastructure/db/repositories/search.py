from typing import List, Dict, Any
import sqlalchemy as db
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.db.models import CleanJobDB, RawJobDB
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class SearchRepository:
    def search_jobs_by_criteria(
        self,
        title: List[str] = None,
        job_level: List[str] = None,
        cities: List[str] = None,
        experience: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Dynamically applies filters based on what the user asked for.
        """
        try:
            with SessionLocal() as session:
                statement = select(CleanJobDB).outerjoin(RawJobDB, RawJobDB.id == CleanJobDB.raw_job_id)
                
                if title:
                    statement = statement.where(CleanJobDB.standardized_title.in_(title))
                if job_level:
                    statement = statement.where(CleanJobDB.job_level.in_(job_level))
                if experience is not None:
                    statement = statement.where(CleanJobDB.experience <= experience)
                if cities:
                    from sqlalchemy import or_
                    city_conditions = [CleanJobDB.cities.cast(db.String).ilike(f"%{city}%") for city in cities]
                    statement = statement.where(or_(*city_conditions))

                statement = statement.limit(limit)
                result = session.execute(statement).scalars().all()

                mapped_jobs = []
                for job in result:
                    mapped_jobs.append({
                        "title": job.standardized_title or "Unknown",
                        "level": job.job_level or "Unknown",
                        "company": job.raw_job.company if job.raw_job else "Unknown",
                        "cities": list(job.cities) if job.cities else [],
                        "experience_required_years": job.experience,
                        "salary_range": f"{job.salary_min or '?'} - {job.salary_max or '?'} {job.currency}",
                        "tech_stack": list(job.tech_stack) if job.tech_stack else [],
                        "url": job.raw_job.url if job.raw_job else "#"
                    })
                return mapped_jobs
        except Exception as e:
            logger.error(f"Failed to search job by criteria: {e}")
            return []
            
    def search_jobs_by_similarity(
        self,
        embedding: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Uses pgvector for Cosine Similarity search.
        """
        try:
            with SessionLocal() as session:
                statement = (
                    select(CleanJobDB)
                    .order_by(CleanJobDB.embedding.op('<=>')(embedding))
                    .limit(limit)
                )
                result = session.execute(statement).scalars().all()
                
                mapped_jobs = []
                for job in result:
                    mapped_jobs.append({
                        "title": job.standardized_title or "Unknown",
                        "level": job.job_level or "Unknown",
                        "company": job.raw_job.company if job.raw_job else "Unknown",
                        "cities": list(job.cities) if job.cities else [],
                        "experience_required_years": job.experience,
                        "salary_range": f"{job.salary_min or '?'} - {job.salary_max or '?'} {job.currency}",
                        "url": job.raw_job.url if job.raw_job else "#",
                        "match_score": 1
                    })
                return mapped_jobs
        except Exception as e:
            logger.error(f"Failed to search jobs by similarity: {e}")
            return []
