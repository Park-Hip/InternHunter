import os
import re
from dotenv import load_dotenv
import json

from src.core.models import ProcessedJob, LLMJobProcess, RawJob
from src.config import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.db.models import CleanJobDB

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google import genai
from google.genai import types
import mlflow

logger = get_logger(__name__)

load_dotenv()

# Configure MLflow if environment variables are set
if os.getenv("MLFLOW_TRACKING_URI"):
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
if os.getenv("MLFLOW_EXPERIMENT"):
    mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT"])
    mlflow.gemini.autolog()

class GeminiClient:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY.get_secret_value()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or passed to constructor.")
            
        self.model = model if model else "gemini-2.5-flash-lite" 
        self.client = genai.Client(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES), 
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def process_raw_job(self, job_data: RawJob) -> ProcessedJob:
        """
        Generates structured job data from raw dictionary.
        """
        try:
            self.job_processor_prompt = mlflow.genai.load_prompt("prompts:/job_processor_prompt/1")
        except Exception as e:
            logger.warning("MLflow prompt load failed, using fallback", error=str(e))
            self.job_processor_prompt = None
        
        raw_context = {}
        description, requirement, benefit = None, None, None  
        
        if job_data.full_json_dump:
            try:
                raw_context = json.loads(job_data.full_json_dump)
                info = raw_context.get("info", "")
                description, requirement, benefit = self._extract_info(info)
            except:
                pass

        if self.job_processor_prompt:
            job_processor_prompt = self.job_processor_prompt.format(
                title = job_data.title or "",
                company = job_data.company or "",
                location = job_data.location or "",
                salary = raw_context.get("salary", ""),
                experience = raw_context.get("experience", ""),
                description = description,
                requirement = requirement,
            )
        else:
            # Fallback
            job_processor_prompt = f"""
            Extract job details for position: {job_data.title} at {job_data.company}.
            Location: {job_data.location}
            Raw Data: {raw_context}
            """

        result = self.client.models.generate_content(
            model=self.model,
            contents=job_processor_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=LLMJobProcess
            )
        )

        if result.parsed:
            # Create ProcessedJob from LLM data + extracted text
            start_date = None # You might want to extract this too if avail
            
            processed_job = ProcessedJob(
                **result.parsed.dict(),
                description=description,
                requirement=requirement,
                benefit=benefit,
            )
            return processed_job
        else:
            raise ValueError("Model returned no parsed result.")

    @staticmethod
    def _extract_info(info: str):
            """Extracts Description, Requirements, and Benefits in info"""
            if not info:
                return None, None, None

            flags = re.DOTALL | re.IGNORECASE

            des_pattern = r"Mô tả công việc(.*?)(?=Yêu cầu ứng viên|$)"
            req_pattern = r"Yêu cầu ứng viên(.*?)(?=Quyền lợi|$)"
            ben_pattern = r"Quyền lợi(.*)"

            des_match = re.search(des_pattern, info, flags)
            req_match = re.search(req_pattern, info, flags)
            ben_match = re.search(ben_pattern, info, flags)

            des = des_match.group(1).strip() if des_match else None
            req = req_match.group(1).strip() if req_match else None
            ben = ben_match.group(1).strip() if ben_match else None

            return des, req, ben

class GroqClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key if api_key else settings.GROQ_API_KEY.get_secret_value()
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set in environment or passed to constructor.")
        self.model = model if model else "openai/gpt-oss-120b"

    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(1, 4, 60),
        retry=retry_if_exception_type(Exception)
    )
    def process_raw_job(job_data: RawJob) -> ProcessedJob:
        if job_data:
            raw_context = job_data.full_json_dump
            info = raw_context.get("info", "")
            description, requirement, benefit = _extract_info(info)

        try:
            self.job_processor_prompt = mlflow.genai.load_prompt("prompts:/job_processor_prompt/2")
        except:
            logger.info("Mlflow prompt loaded failed.")

        if self.job_processor_prompt:
            self.job_processor_prompt = self.job_processor_prompt.format(
                title=raw_context.title,
                company=raw_context.company,
                location=raw_context.location,
                salary=raw_context.salary,
                experience=raw_context.experience,
                description=description,
                requirement=requirement
            )

    @staticmethod
    def _extract_info(info: str):
            """Extracts Description, Requirements, and Benefits in info"""
            if not info:
                return None, None, None

            flags = re.DOTALL | re.IGNORECASE

            des_pattern = r"Mô tả công việc(.*?)(?=Yêu cầu ứng viên|$)"
            req_pattern = r"Yêu cầu ứng viên(.*?)(?=Quyền lợi|$)"
            ben_pattern = r"Quyền lợi(.*)"

            des_match = re.search(des_pattern, info, flags)
            req_match = re.search(req_pattern, info, flags)
            ben_match = re.search(ben_pattern, info, flags)

            des = des_match.group(1).strip() if des_match else None
            req = req_match.group(1).strip() if req_match else None
            ben = ben_match.group(1).strip() if ben_match else None

            return des, req, ben


