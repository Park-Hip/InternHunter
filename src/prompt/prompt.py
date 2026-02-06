import mlflow
import logging
import sys
import os
from dotenv import load_dotenv
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [PROMPT_REGISTRY] - %(levelname)s - %(filename)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT"])

job_parser_prompt = """
You are an expert AI Recruitment Data Parser. Your job is to extract structured data from raw job descriptions.

### EXTRACTION RULES:

1. **Locations (Cities):** - Normalize Vietnamese cities to standard English formats: "Hanoi", "Ho Chi Minh", "Da Nang". 
   - If "Remote" is mentioned, include "Remote" in the list.

2. **Salary Parsing:**
   - If the salary is "Thỏa thuận", "Negotiable", or "Deal": Set `is_salary_negotiable` = True, `salary_min` = None, `salary_max` = None.
   - If a range is given (e.g., "10 - 15 triệu"): Set `salary_min` = 10, `salary_max` = 15.
   - If "Up to 1000 USD": Set `salary_max` = 25 (approx convert to Million VND) or keep original scale if consistent. **Standardize to Million VND if possible.**
   - If only a minimum is given ("From 1000$"): Set `salary_min` = 25, `salary_max` = None.

3. **Experience:**
   - Extract strictly numeric years for `min_years_experience` (e.g., "1+ year" -> 1.0).
   - If "Intern" or "Fresher", set `min_years_experience` = 0.0.

4. **Skills vs. Domain:**
   - `tech_stack`: Specific tools/languages (Python, AWS, React, Docker, SQL).
   - `domain_knowledge`: Concepts/Industries (Banking, Computer Vision, NLP, E-commerce, Agile).

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
**INFO:** {{ info }}
---
"""

def register_prompt(prompt_name: str) -> Any:
    logger.info("Attempting to register prompt...")

    try:
        prompt_info = mlflow.genai.register_prompt(
            name=prompt_name,
            template=job_parser_prompt,
            commit_message="Initial commit",
            tags={
                "author": "Park-Hip",
                "language": "en",
                "use_case": "job parser",
            }
        )
        logger.info(f"Prompt successfully registered!")
        logger.info(f"Prompt Name: {prompt_info.name}")
        logger.info(f"Version: {prompt_info.version}")
        return prompt_info

    except Exception as e:
        logger.error(f"Failed to register prompt: {e}")
        raise e

if __name__ == "__main__":
    prompt_name = "job_parser_prompt"
    register_prompt(prompt_name)