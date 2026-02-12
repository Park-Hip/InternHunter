from typing import Literal
from src.infrastructure.llm.providers import GeminiClient
from src.config import settings

class LLMRouter:
    """
    Routes requests to the appropriate LLM provider.
    Future extension: Load balance between Gemini and Groq, or fallback logic.
    """
    def __init__(self):
        self._gemini = None
    
    def get_client(self, provider: Literal["gemini", "groq"] = "gemini"):
        if provider == "gemini":
            if not self._gemini:
                self._gemini = GeminiClient()
            return self._gemini
        
        # Placeholder for Groq
        # elif provider == "groq": ...
        
        raise ValueError(f"Unknown provider: {provider}")

# Singleton router
llm_router = LLMRouter()