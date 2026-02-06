from typing import Optional, List
from pydantic import BaseModel, Field


class StandardJob(BaseModel):
    standardized_title: str = Field(..., description="A standard role title, e.g. AI Engineer, Data Scientist.")
    job_level: Optional[str] = Field(None, description="Job level, e.g., Fresher, Junior, Senior, Manager.")
    is_internship: bool = Field(..., description="True if this is an intern/fresher position.")
    cities: List[str] = Field(..., description="List of cities where the candidate must work, e.g., ['Hanoi', 'Ho Chi Minh'].")

    min_years_experience: float = Field(0.0, description="Numeric minimum years required. Use 0 for freshers/interns/no requirement.")
    min_gpa: Optional[float] = Field(None, description="Minimum GPA if mentioned (scale 4.0).")
    english_requirement: Optional[str] = Field(None, description="English requirement, e.g., 'TOEIC 600', 'Fluent'.")

    salary_min: Optional[float] = Field(None,  description="Minimum salary value (in Million VND or USD). Null if 'Thỏa thuận'.")
    salary_max: Optional[float] = Field(None, description="Maximum salary value. Null if 'Thỏa thuận'.")
    is_salary_negotiable: bool = Field(False, description="True if salary is described as 'Thỏa thuận', 'Deal', or 'Negotiable'.")

    tech_stack: List[str] = Field(..., description="List of specific technical skills (Python, PyTorch, AWS, etc.).")
    domain_knowledge: List[str] = Field(..., description="Business domains or concepts (e.g., Computer Vision, NLP, Banking).")


