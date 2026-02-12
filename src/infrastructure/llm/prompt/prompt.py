import mlflow
import sys
import os
from dotenv import load_dotenv
from typing import Any

from src.infrastructure.logging import get_logger, configure_logging
from src.config import settings

logger = get_logger(__name__)

load_dotenv()

mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)

job_processor_prompt = """
You are an expert AI Recruitment Data Parser. Your job is to extract structured data from raw job descriptions.

### EXTRACTION RULES:

1. **Locations (Cities):** - Normalize Vietnamese cities to standard English formats: "Hanoi", "Ho Chi Minh", "Da Nang". 

2. **Salary Parsing:**
   - If the salary is "Thỏa thuận", "Negotiable", or "Deal": Set `is_salary_negotiable` = True, `salary_min` = None, `salary_max` = None.
   - If a range is given (e.g., "10 - 15 triệu"): Set `salary_min` = 10, `salary_max` = 15.
   - Currency can be either 'VND' or '$'
   - If only a minimum is given ("From 1000$"): Set `salary_min` = 26, `salary_max` = None.

3. **Experience:**
   - Extract strictly numeric years for `min_years_experience` (e.g., "1+ year" -> 1.0).
   - If "Intern" or "Fresher", set `min_years_experience` = 0.0.

4. **Skills vs. Domain:**
   - `tech_stack`: Specific tools/languages (Python, AWS, React, Docker, SQL).
   - `technical_competencies`: Brief, standardized actions (Finetune LLMs, Evaluate models, Deploy models)
   - `domain_knowledge`: Concepts/Industries (Banking, Computer Vision, Natural Language Processing, E-commerce, Agile).

5. **English Requirements:**
   - Extract specific certificates if mentioned ("TOEIC 600", "IELTS 6.5").
   - If generic ("Good English"), return "Fluent" or "Intermediate".

### OUTPUT FORMAT:
Return strictly valid JSON matching the provided schema. Handle nulls gracefully.

Here is the raw job text. Analyze it:

---
**TITLE:** {{ title }}
**COMPANY:** {{ company }}
**LOCATION (Raw):** {{ location }}
**SALARY:** {{ salary }}
**EXPERIENCE:** {{ experience }}
**DESCRIPTION:** {{ description }}
**REQUIREMENT:** {{ requirement }}
---
"""

def register_prompt(prompt_name: str) -> Any:
    logger.info("Attempting to register prompt")

    try:
        prompt_info = mlflow.genai.register_prompt(
            name=prompt_name,
            template=job_processor_prompt,
            commit_message="Initial commit",
            tags={
                "author": "Park-Hip",
                "language": "en",
                "use_case": "job processor",
            }
        )
        logger.info("Prompt successfully registered")
        logger.info("Prompt details", name=prompt_info.name, version=prompt_info.version)
        return prompt_info

    except Exception as e:
        logger.error("Prompt registration failed", error=str(e), exc_info=True)
        raise e

if __name__ == "__main__":
    configure_logging()
    prompt_name = "job_processor_prompt"
    register_prompt(prompt_name)