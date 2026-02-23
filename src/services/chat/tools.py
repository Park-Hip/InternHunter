from typing import List, Dict, Any
from pydantic import BaseModel, Field, Literal

from src.infrastructure.db.repository import JobRepository
from src.infrastructure.logging import get_logger
from src.services.chat.tool_registry import register_tool

logger = get_logger(__name__)

repo = JobRepository()

class SearchJobsArgs(BaseModel):
    title: List[str] = Field(None, description="A list of job titles to search for (e.g., ['Data Scientist', 'AI Engineer']).")
    experience: int = Field(None, description="The maximum years of experience required for the role.")
    job_level: List[Literal["Intern", "Junior", "Middle", "Senior"]] = Field(None, description="A list of job levels.")
    cities: List[str] = Field(None, description="A list of cities that employees can work in.")
    limit: int = Field(10, description="The maximum number of jobs to fetch.")

@register_tool(
    name="search_jobs",
    description="Searches the database for jobs based on criteria like title, experience required, or city. Use this when the user asks to find specific types of jobs.",
    args_schema=SearchJobsArgs
)
def execute_search_jobs(
    title: List[str] = None,
    job_level: List[str] = None,
    cities: List[str] = None,
    experience: int = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    try:
        result = repo.search_jobs_by_criteria(title, job_level, cities, experience)
        return result
    except Exception as e:
        logger.error("execute_search_jobs tool failed", error=str(e))
        return {"error": "Failed to execute_search_jobs"}

