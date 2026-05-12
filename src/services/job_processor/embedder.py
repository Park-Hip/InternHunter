from google import genai
from google.genai import types
from tenacity import wait_exponential, retry, stop_after_attempt, retry_if_exception_type
from typing import List
from langdetect import detect

from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.infrastructure.llm.router import llm_router

logger = get_logger(__name__)

class Embedder:
    def __init__(self):
        if isinstance(settings.GEMINI_API_KEY, str):
            self.api_key = settings.GEMINI_API_KEY
        else:
            self.api_key = settings.GEMINI_API_KEY.get_secret_value()
            
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or passed to constructor.")
        self.client = genai.Client(api_key=self.api_key)
        self.router = llm_router

    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def generate_embedding(self, text: str) -> List[float]:
        try:
            lan = detect(text)
        except Exception:
            lan = "en"

        if lan != "en":
            try:
                text = self.router.translate_with_fallback(text)
            except Exception as e:
                logger.warning(f"Translation failed, using original text: {e}")

        try:
            result = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY", output_dimensionality=768),
            )
            
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Fail to generate embedding: {e}")
            raise

embedder = Embedder()
