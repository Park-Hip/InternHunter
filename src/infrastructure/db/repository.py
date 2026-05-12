import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import sqlalchemy as db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, and_, text

from src.infrastructure.db.session import engine, SessionLocal
from src.infrastructure.db.models import Base, RawJobDB, CleanJobDB, ChatSessionDB, ChatMessageDB, UserProfileDB, AuditJobDB
from src.core.models import ProcessedJob, RawJob
from src.core.models.chat import Message
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

class JobRepository:
    def create_tables(self):
        """Create raw_jobs and clean_jobs tables."""
        Base.metadata.create_all(bind=engine)
        self._sync_sequences()
        logger.info("Database tables verified/created")

    def _sync_sequences(self):
        """Reset PostgreSQL auto-increment sequences to match current max IDs.
        
        Prevents 'duplicate key value violates unique constraint' errors
        caused by sequences being out of sync after migrations or manual inserts.
        """
        tables = ["raw_jobs", "clean_jobs"]
        with SessionLocal() as session:
            for table in tables:
                try:
                    # pg_get_serial_sequence returns the sequence name for the column
                    seq_query = text(
                        "SELECT pg_get_serial_sequence(:table, 'id')"
                    )
                    seq_name = session.execute(seq_query, {"table": table}).scalar()
                    if not seq_name:
                        continue

                    # Reset sequence to MAX(id) + 1 (or 1 if table is empty)
                    reset_query = text(
                        f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                    )
                    new_val = session.execute(reset_query).scalar()
                    session.commit()
                    logger.info("Sequence synced", table=table, sequence=seq_name, next_val=new_val)
                except Exception as e:
                    session.rollback()
                    logger.warning("Failed to sync sequence", table=table, error=str(e))

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

    def get_raw_job_by_id(self, raw_job_id) -> RawJob:
        with SessionLocal() as session:
            try:
                statement = select(RawJobDB).where(RawJobDB.id == None)
                result = session.execute(statement).scalar()
                return result
            except Exception as e:
                logger.error("Falied to get raw job by id", error=str(e))

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
                    title=job_data.get('title'),
                    company=job_data.get('company'),
                    location=job_data.get('location'),
                    full_json_dump=job_data.get('full_json_dump'),
                    status=job_data.get('status', 'pending'),
                    extraction_method=job_data.get('extraction_method', 'css'),
                    raw_markdown=job_data.get('raw_markdown'),
                    retry_count=job_data.get('retry_count', 0)
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

    def save_to_audit(self, audit_data: Dict[str, Any]) -> bool:
        """Saves a failed job entry to the audit_jobs (DLQ)."""
        with SessionLocal() as session:
            try:
                audit_entry = AuditJobDB(
                    url=audit_data['url'],
                    error_type=audit_data.get('error_type'),
                    error_message=audit_data.get('error_message'),
                    screenshot_path=audit_data.get('screenshot_path'),
                    html_content=audit_data.get('html_content')
                )
                session.add(audit_entry)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save to audit: {e}")
                return False

    def fetch_pending_raw_jobs(self, limit: int = 100) -> List[RawJob]:
        """Fetches jobs that are 'pending' and need processing."""
        with SessionLocal() as session:
            try:
                statement = select(RawJobDB).where(RawJobDB.status == "pending").limit(limit)
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
                        status=row.status,
                        extraction_method=row.extraction_method,
                        raw_markdown=row.raw_markdown,
                        retry_count=row.retry_count,
                        created_at=row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                return jobs
            except Exception as e:
                logger.error(f"Error fetching pending raw jobs: {e}")
                return []

    def update_job_status(self, job_id: int, status: str, retry_increment: bool = False) -> bool:
        """Updates the status of a raw job."""
        with SessionLocal() as session:
            try:
                job = session.get(RawJobDB, job_id)
                if job:
                    job.status = status
                    if retry_increment:
                        job.retry_count += 1
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to update job status: {e}")
                return False

    def fetch_unparsed_jobs(self, limit: int = 100) -> List[RawJob]:
        """Fetches jobs that have not been parsed yet (not in clean_jobs)."""
        with SessionLocal() as session:
            try:
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
                        status=row.status,
                        extraction_method=row.extraction_method,
                        raw_markdown=row.raw_markdown,
                        retry_count=row.retry_count,
                        created_at=row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ))
                return jobs
            except Exception as e:
                logger.error(f"Error fetching unparsed jobs: {e}")
                return []

    def save_parsed_job(self, parsed: ProcessedJob, raw_job_id: int, original_url: str, embedding: list = None) -> bool:
        """Saves parsed job data with proper relationships and optional embedding."""
        with SessionLocal() as session:
            try:
                # Guard: skip if a clean_job already exists for this raw_job
                existing = session.execute(
                    select(CleanJobDB).where(CleanJobDB.raw_job_id == raw_job_id)
                ).scalar_one_or_none()
                if existing:
                    logger.warning("Clean job already exists, skipping", raw_job_id=raw_job_id, url=original_url)
                    return True

                clean_job = CleanJobDB(
                    raw_job_id=raw_job_id,
                    standardized_title=parsed.standardized_title,
                    job_level=parsed.job_level,
                    is_internship=parsed.is_internship,
                    description=parsed.description,
                    requirement=parsed.requirement,
                    benefit=parsed.benefit,
                    cities=parsed.cities,
                    experience=parsed.experience,
                    min_gpa=parsed.min_gpa,
                    english_requirement=parsed.english_requirement,
                    salary_min=parsed.salary_min,
                    salary_max=parsed.salary_max,
                    currency=parsed.currency,
                    is_salary_negotiable=parsed.is_salary_negotiable,
                    tech_stack=parsed.tech_stack,
                    technical_competencies=parsed.technical_competencies,
                    domain_knowledge=parsed.domain_knowledge,
                    embedding=embedding,
                )
                session.add(clean_job)
                session.commit()
                return True
            except IntegrityError as e:
                session.rollback()
                logger.error("Integrity error saving parsed job", original_url=original_url, error=str(e))
                return False
            except Exception as e:
                session.rollback()
                logger.error("Failed to save parsed job", original_url=original_url, error=str(e))
                return False

    # Function for agents to use
    def search_jobs_by_criteria(
        self,
        title: List[str] = None,
        job_level: List[str] = None, # Avoid importing Literal here just to keep model separation clean, validation happens at Pydantic level
        cities: List[str] = None,
        experience: int = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tool meant specifically for the AI agent to search jobs safely.
        Dynamically applies filters based on what the user asked for.
        """
        try:
            with SessionLocal() as session:
                statement = select(CleanJobDB).outerjoin(RawJobDB, RawJobDB.id == CleanJobDB.raw_job_id)
                
                # 2. Dynamic AND conditions
                if title:
                    statement = statement.where(CleanJobDB.standardized_title.in_(title))
                
                if job_level:
                    statement = statement.where(CleanJobDB.job_level.in_(job_level))

                if experience is not None:
                    statement = statement.where(CleanJobDB.experience <= experience)

                if cities:
                    # Handle searching inside a JSON column.
                    # This casts the JSON 'cities' column to text and checks if the requested city is a substring.
                    # It creates an OR condition for the cities requested.
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
        Tool meant specifically for the AI agent to search jobs by vector similarity.
        Uses pgvector for Cosine Similarity search.
        """
        try:
            with SessionLocal() as session:
                # pgvector cosine similarity operator <=>
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
                        "match_score": 1 # Placeholder for score calculation if needed
                    })
                return mapped_jobs
        except Exception as e:
            logger.error(f"Failed to search jobs by similarity: {e}")
            return []

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as session:
            try:
                statement = select(UserProfileDB).where(UserProfileDB.user_id == user_id)
                profile = session.execute(statement).scalar_one_or_none()
                if profile:
                    return {
                        "user_id": profile.user_id,
                        "resume_text": profile.resume_text,
                        "resume_embedding": profile.resume_embedding
                    }
                return None
            except Exception as e:
                logger.error(f"Failed to get user profile: {e}")
                return None

    def save_user_profile(self, user_id: str, resume_text: str, embedding: List[float]) -> bool:
        with SessionLocal() as session:
            try:
                statement = select(UserProfileDB).where(UserProfileDB.user_id == user_id)
                profile = session.execute(statement).scalar_one_or_none()
                
                if profile:
                    profile.resume_text = resume_text
                    profile.resume_embedding = embedding
                else:
                    profile = UserProfileDB(
                        user_id=user_id,
                        resume_text=resume_text,
                        resume_embedding=embedding
                    )
                    session.add(profile)
                
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save user profile: {e}")
                return False
            

    @staticmethod
    def normalize_url(url: str) -> str:
        """Canonical URL for dedup (strip query/fragment and whitespace)."""
        if not url or not isinstance(url, str):
            return ""
        return url.split("?")[0].split("#")[0].strip()

class MemoryRepository:
    def create_tables(self):
        """Create raw_jobs and clean_jobs tables."""
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created")

    def load_messages(self, session_id: str, limit: int = 10) -> List[Message]:
        with SessionLocal() as session:
            try:
                statement = (
                    select(ChatMessageDB)
                    .where(ChatMessageDB.session_id == session_id)
                    .order_by(ChatMessageDB.created_at.desc())
                    .limit(limit)
                )
                result = session.execute(statement).scalars().all()
                messages = reversed(result)

                return [
                    Message(
                        role=m.role,
                        content=m.content,
                        tool_calls=m.tool_calls,
                        tool_call_id=m.tool_call_id
                    ) for m in messages
                ]
            except Exception as e:
                logger.error("Failed to load messages from ChatMessageDB", error=str(e))
                raise

    def save_messages(self, session_id: str, messages: List[Message], limit: int = 10):
        with SessionLocal() as session:
            try:
                statement = select(ChatSessionDB).where(ChatSessionDB.id == session_id)
                chat_session = session.execute(statement).scalar_one_or_none()
                if not chat_session:
                    user_id = None
                    for m in messages:
                        if m.user_id:
                            user_id = m.user_id
                            break
                    chat_session = ChatSessionDB(id=session_id, user_id=user_id)
                    session.add(chat_session)
                    session.commit()

                if len(messages) > limit:
                    messages = messages[-limit:]
                    
                for message in messages:
                    new_message = ChatMessageDB(
                        role = message.role,
                        content = message.content,
                        user_id = message.user_id,
                        session_id = session_id,
                        tokens_used = message.tokens_used,
                        tool_calls = message.tool_calls,
                        tool_call_id = message.tool_call_id
                    )
                    session.add(new_message)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error("Failed save messages to ChatMessageDB", error=str(e))

    def get_user_sessions(self, user_id: str) -> List[dict]:
        with SessionLocal() as session:
            try:
                statement = select(ChatSessionDB).where(ChatSessionDB.user_id == user_id)
                chat_sessions = session.execute(statement).scalars().all()
                return [
                    {
                        "session_id": s.id,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in chat_sessions
                ]
            except Exception as e:
                logger.error("Failed to get_user_sessions", error=str(e))
                raise

    def delete_session(self, session_id: str) -> bool:
        from sqlalchemy import delete
        with SessionLocal() as session:
            try:
                statement = delete(ChatSessionDB).where(ChatSessionDB.id == session_id)
                session.execute(statement)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error("delete_session failed", error=str(e))
                raise

