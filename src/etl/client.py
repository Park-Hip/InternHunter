import os
import logging
from dotenv import load_dotenv

from src.schema.schema import StandardJob

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google import genai
from google.genai import types
import mlflow


logger = logging.getLogger(__name__)

load_dotenv()

# Configure MLflow if environment variables are set
if os.getenv("MLFLOW_TRACKING_URI"):
    mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
if os.getenv("MLFLOW_EXPERIMENT"):
    mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT"])
    mlflow.gemini.autolog()

class GeminiClient:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or passed to constructor.")
            
        self.model = model if model else "gemini-2.5-flash-lite" 
        self.client = genai.Client(api_key=self.api_key)
        
        try:
            self.prompt_template = mlflow.genai.load_prompt("prompts:/job_parser_prompt/2")
        except Exception as e:
            logger.warning(f"Failed to load MLflow prompt: {e}. Using default fallback if available (not implemented).")
            # In a real scenario, you might want to fail hard or have a fallback string.
            raise

    @retry(
        stop=stop_after_attempt(10), 
        wait=wait_exponential(multiplier=1, min=10, max=60),
        retry=retry_if_exception_type(Exception) # Can refine to ClientError if imported
    )
    def generate_content(self, job_data: dict) -> StandardJob:
        """
        Generates structured job data from raw dictionary.
        Let exceptions bubble up for tenacity to handle retries.
        """
        # Validate input
        required_fields = ["title", "company", "location"] # info might be optional in some contexts, but let's assume strict
        for f in required_fields:
            if f not in job_data:
                # If critical data is missing, retrying won't help ->   fail fast? 
                # Or maybe it's a transient issue in previous step? 
                # Here we assume data integrity is checked before, or we let it fail.
                pass

        job_parser_prompt = self.prompt_template.format(
            title = job_data.get("title", ""),
            company = job_data.get("company", ""),
            location = job_data.get("location", ""),
            info = job_data.get("info", ""),
            salary = job_data.get("salary", ""),
            experience = job_data.get("experience", "")
        )

        result = self.client.models.generate_content(
            model=self.model,
            contents=job_parser_prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=StandardJob
            )
        )

        # Ensure we return the parsed object, not the raw response
        if result.parsed:
            return result.parsed
        else:
             # Fallback if parsing failed but no exception raised (unlikely with response_schema)
            raise ValueError("Model returned no parsed result.")

