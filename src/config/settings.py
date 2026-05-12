import os
import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Any, Dict

class Settings(BaseSettings):
    # --- Environment Variables (via .env) ---
    GEMINI_API_KEY: SecretStr
    GROQ_API_KEY: SecretStr
    DB_URL: SecretStr
    DS_URL: str = "https://www.topcv.vn/tim-viec-lam-data-scientist?sba=1"
    AIE_URL: str = "https://www.topcv.vn/tim-viec-lam-ai-engineer?sba=1"

    # --- Application Metadata ---
    APP_NAME: str = "job-finder"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Placeholders for YAML data
    config_yaml: Dict[str, Any] = {}
    prompts_yaml: Dict[str, Any] = {}

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

    def get_prompt(self, name: str) -> str:
        """Helper to get a prompt from the loaded prompts YAML."""
        return self.prompts_yaml.get("prompts", {}).get(name, "")

def load_settings() -> Settings:
    settings = Settings()
    
    # Path relative to project root
    config_path = settings.BASE_DIR / "src" / "config" / "settings.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            settings.config_yaml = yaml.safe_load(f) or {}
            
    prompts_path = settings.BASE_DIR / "src" / "config" / "prompts.yaml"
    if prompts_path.exists():
        with open(prompts_path, "r", encoding="utf-8") as f:
            settings.prompts_yaml = yaml.safe_load(f) or {}
            
    return settings

settings = load_settings()
