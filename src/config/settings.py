import os
import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, SecretStr

class CrawlerSettings(BaseModel):
    rate_limit_rpm: int = 20
    max_retries: int = 3
    max_pages: int = 5  # Max search result pages to scrape per URL
    extract_delay_min: float = 10.0  # Min seconds between detail extractions
    extract_delay_max: float = 15.0  # Max seconds between detail extractions

class Settings(BaseSettings):
    # --- Environment Variables (via .env) ---
    GEMINI_API_KEY: SecretStr
    GROQ_API_KEY: SecretStr
    DB_URL: SecretStr
    DS_URL: str = "https://www.topcv.vn/tim-viec-lam-data-scientist?sba=1"
    AIE_URL: str = "https://www.topcv.vn/tim-viec-lam-ai-engineer?sba=1"

    @property
    def search_urls(self) -> list[str]:
        """All search URLs to scrape. Centralizes URL management."""
        return [self.DS_URL, self.AIE_URL]

    # --- Application Metadata ---
    APP_NAME: str = "job-finder"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # --- Type-Safe Configs ---
    crawler: CrawlerSettings = CrawlerSettings()

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
            yaml_data = yaml.safe_load(f) or {}
            settings.config_yaml = yaml_data
            if "crawler" in yaml_data:
                settings.crawler = CrawlerSettings(**yaml_data["crawler"])
            
    prompts_path = settings.BASE_DIR / "src" / "config" / "prompts.yaml"
    if prompts_path.exists():
        with open(prompts_path, "r", encoding="utf-8") as f:
            settings.prompts_yaml = yaml.safe_load(f) or {}
            
    return settings

settings = load_settings()
