import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import sqlalchemy as db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, and_

from src.infrastructure.db.session import engine, SessionLocal
from src.infrastructure.db.models import Base, RawJobDB, CleanJobDB
from src.core.models import ProcessedJob, RawJob
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class JobRepository:
    def create_tables(self):
        """Create raw_jobs and clean_jobs tables."""
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")

    def get_raw_jobs_count(self) -> int:
        """Returns the total count of raw jobs in the database."""
        with SessionLocal() as session:
            try:
                # select(func.count()) returns a Select object, need to execute it.
                statement = select(func.count()).select_from(RawJobDB)
                result = session.execute(statement).scalar()
                return result if result else 0
            except Exception as e:
                logger.error(f"Error counting raw jobs: {e}")
                return 0

    def filter_new_links(self, unfiltered_links: List[dict]) -> List[dict]:
        """Filters out links that already exist in the raw_jobs."""
        if not unfiltered_links:
            return []

        # Normalize and prepare potential new links
        normalized_links_map = {}
        for link in unfiltered_links:
            url = link.get('url', '')
            norm = self.normalize_url(url)
            if norm:
                normalized_links_map[norm] = link

        if not normalized_links_map:
            return []

        potential_urls = list(normalized_links_map.keys())
        
        # Batch check existence
        new_links = []
        with SessionLocal() as session:
            try:
                # Query strictly for URLs that are in our potential list
                # Depending on DB size, chunking might be needed, but for now this is fine.
                statement = select(RawJobDB.url).where(RawJobDB.url.in_(potential_urls))
                existing_urls_result = session.execute(statement).scalars().all()
                existing_urls = set(existing_urls_result)

                for url, link in normalized_links_map.items():
                    if url not in existing_urls:
                        link['url'] = url # Ensure strict normalized URL usage
                        new_links.append(link)

            except Exception as e:
                logger.error(f"Error filtering new links: {e}")
                # Fallback: return everything or nothing? Safe to return nothing to avoid crashing, 
                # but might miss data. Returning nothing prevents duplicate DB errors later, hopefully.
                return []

        return new_links

    def save_raw_job(self, job_data: Dict[str, Any]) -> bool:
        """Saves a single raw job to the database."""
        with SessionLocal() as session:
            try:
                raw_job = RawJobDB(
                    url=job_data['url'],
                    title=job_data['title'],
                    company=job_data['company'],
                    location=job_data['location'],
                    full_json_dump=job_data['full_json_dump'] # SQLAlchemy handles JSON serialization for JSON type
                )
                session.add(raw_job)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                logger.warning(f"Duplicate job found (URL collision): {job_data.get('url')}")
                return False
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save raw job {job_data.get('url')}: {e}")
                return False

    def fetch_unparsed_jobs(self, limit: int = 100) -> List[RawJob]:
        """Fetches jobs that have not been parsed yet (not in clean_jobs)."""
        with SessionLocal() as session:
            try:
                # Left join raw_jobs with clean_jobs where clean_jobs.id is null
                statement = (
                    select(RawJobDB)
                    .outerjoin(CleanJobDB, RawJobDB.id == CleanJobDB.raw_job_id)
                    .where(CleanJobDB.id == None)
                    .limit(limit)
                )
                
                results = session.execute(statement).scalars().all()
                
                jobs = []
                for row in results:
                    jobs.append(RawJob(
                        id=row.id,
                        url=row.url,
                        title=row.title,
                        company=row.company,
                        location=row.location,
                        full_json_dump=json.dumps(row.full_json_dump) if row.full_json_dump else "{}",
                        created_at=row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                return jobs
            except Exception as e:
                logger.error(f"Error fetching unparsed jobs: {e}")
                return []

    def save_parsed_job(self, parsed: ProcessedJob, raw_job_id: int, original_url: str) -> bool:
        """Saves parsed job data with proper relationships."""
        with SessionLocal() as session:
            try:
                clean_job = CleanJobDB(
                    raw_job_id=raw_job_id,
                    standardized_title=parsed.standardized_title,
                    job_level=parsed.job_level,
                    is_internship=parsed.is_internship,
                    description=parsed.description,
                    requirement=parsed.requirement,
                    benefit=parsed.benefit,
                    cities=parsed.cities, # SQLAlchemy JSON type handles list/dict
                    experience=parsed.experience,
                    min_gpa=parsed.min_gpa,
                    english_requirement=parsed.english_requirement,
                    salary_min=parsed.salary_min,
                    salary_max=parsed.salary_max,
                    currency=parsed.currency,
                    is_salary_negotiable=parsed.is_salary_negotiable,
                    tech_stack=parsed.tech_stack, # SQLAlchemy JSON type
                    technical_competencies=parsed.technical_competencies, # SQLAlchemy JSON type
                    domain_knowledge=parsed.domain_knowledge # SQLAlchemy JSON type
                )
                session.add(clean_job)
                session.commit()
                return True
            except IntegrityError as e:
                session.rollback()
                logger.error(f"Integrity error saving parsed job for {original_url}: {e}")
                return False
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save parsed job for {original_url}: {e}")
                return False

    @staticmethod
    def normalize_url(url: str) -> str:
        """Canonical URL for dedup (strip query/fragment and whitespace)."""
        if not url or not isinstance(url, str):
            return ""
        return url.split("?")[0].split("#")[0].strip()
