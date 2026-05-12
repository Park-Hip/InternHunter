import os
import json

from src.core.models import ProcessedJob, LLMJobProcess, RawJob
from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.llm.base import LLMProvider

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google import genai
from google.genai import types
from groq import Groq

logger = get_logger(__name__)

try:
    import mlflow
    mlflow_cfg = settings.config_yaml.get("mlflow", {})
    if mlflow_cfg.get("tracking_uri"):
        mlflow.set_tracking_uri(mlflow_cfg.get("tracking_uri"))
    if mlflow_cfg.get("experiment"):
        mlflow.set_experiment(mlflow_cfg.get("experiment"))
    _mlflow_available = True
except ImportError:
    _mlflow_available = False
    logger.info("MLflow not available, skipping autolog setup.")


def _load_prompt(prompt_name: str = "job_processor"):
    """Load prompt template from centralized settings."""
    return settings.get_prompt(prompt_name)


def _build_prompt(prompt_template, job_data: RawJob, raw_context: dict, description, requirement):
    """Build the final prompt string from template or fallback."""
    if prompt_template:
        from jinja2 import Template
        template = Template(prompt_template)
        return template.render(
            title=job_data.title or "",
            company=job_data.company or "",
            location=job_data.location or "",
            salary=raw_context.get("salary", ""),
            experience=raw_context.get("experience", ""),
            description=description,
            requirement=requirement,
        )
    else:
        return f"""
        Extract job details for position: {job_data.title} at {job_data.company}.
        Location: {job_data.location}
        Raw Data: {raw_context}
        """

# ============================================================
# Gemini Provider
# ============================================================
class GeminiClient(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or settings.GEMINI_API_KEY.get_secret_value()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or passed to constructor.")

        cfg = settings.config_yaml.get("llm", {}).get("gemini", {})
        self.model = model or cfg.get("model", "gemini-2.5-flash-lite")
        self.temperature = cfg.get("temperature", 0.1)
        self.max_tokens = cfg.get("max_tokens", 2048)
        
        self.client = genai.Client(api_key=self.api_key)
        mlflow.gemini.autolog()

    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def process_raw_job(self, job_data: RawJob) -> ProcessedJob:
        """Generates structured job data from raw dictionary using Gemini."""
        raw_context, description, requirement, benefit = self._prepare_job_context(job_data)

        prompt_template = _load_prompt(prompt_name="job_processor")
        job_processor_prompt = _build_prompt(prompt_template, job_data, raw_context, description, requirement)

        result = self.client.models.generate_content(
            model=self.model,
            contents=job_processor_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=LLMJobProcess,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        )

        if result.parsed:
            processed_job = ProcessedJob(
                **result.parsed.dict(),
                description=description,
                requirement=requirement,
                benefit=benefit,
            )
            return processed_job
        else:
            raise ValueError("Model returned no parsed result.")

    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def translate(self, text: str) -> str:
        """Translate text to English using Gemini."""
        try:
            result = self.client.models.generate_content(
                model=self.model,
                contents=f"Translate the following job description to English. Do not add any preamble or explanation:\n\n{text}",
            )
            return result.text.strip()
        except Exception as e:
            logger.error("Translation failed", error=str(e))
            raise


# ============================================================
# Groq Provider
# ============================================================
class GroqClient(LLMProvider):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key if api_key else settings.GROQ_API_KEY.get_secret_value()
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set in environment or passed to constructor.")
        
        cfg = settings.config_yaml.get("llm", {}).get("groq", {})
        self.model = model or cfg.get("model", "llama-3.3-70b-versatile")
        self.temperature = cfg.get("temperature", 0.0)
        self.max_tokens = cfg.get("max_tokens", 1024)
        
        self.client = Groq(api_key=self.api_key)

    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def process_raw_job(self, job_data: RawJob) -> ProcessedJob:
        """Generates structured job data from raw dictionary using Groq."""
        raw_context, description, requirement, benefit = self._prepare_job_context(job_data)

        prompt_template = _load_prompt(prompt_name="job_processor")
        job_processor_prompt = _build_prompt(prompt_template, job_data, raw_context, description, requirement)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Extract the details in the job data."},
                {"role": "user", "content": job_processor_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "job_process",
                    "schema": LLMJobProcess.model_json_schema()
                }
            },
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )

        result = json.loads(response.choices[0].message.content)

        if result:
            processed_job = ProcessedJob(
                **result,
                description=description,
                requirement=requirement,
                benefit=benefit,
            )
            return processed_job
        else:
            raise ValueError("Model returned no parsed result.")

    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def translate(self, text: str) -> str:
        """Translate text to English using Groq."""
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Translate the following job description to English. Do not add any preamble or explanation."},
                    {"role": "user", "content": text},
                ]
            )
            return result.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Translation failed", error=str(e))
            raise
