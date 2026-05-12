from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class CrawlerSettings(BaseModel):
    rate_limit_rpm: int = 20
    max_retries: int = 3
    max_pages: int = 5
    extract_delay_min: float = 10.0
    extract_delay_max: float = 15.0


class Settings(BaseSettings):
    GEMINI_API_KEY: SecretStr | None = None
    GROQ_API_KEY: SecretStr | None = None
    DB_URL: SecretStr | None = None
    DS_URL: str = "https://www.topcv.vn/tim-viec-lam-data-scientist?sba=1"
    AIE_URL: str = "https://www.topcv.vn/tim-viec-lam-ai-engineer?sba=1"

    APP_NAME: str = "internhunter"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    BASE_DIR: Path = Path(__file__).resolve().parents[3]

    crawler: CrawlerSettings = CrawlerSettings()
    config_yaml: Dict[str, Any] = {}
    prompts_yaml: Dict[str, Any] = {}

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )

    @property
    def search_urls(self) -> list[str]:
        return [self.DS_URL, self.AIE_URL]

    def get_prompt(self, name: str) -> str:
        return self.prompts_yaml.get("prompts", {}).get(name, "")


def load_settings() -> Settings:
    loaded = Settings()

    config_path = loaded.BASE_DIR / "src" / "config" / "settings.yaml"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            config_yaml = yaml.safe_load(f) or {}
            loaded.config_yaml = config_yaml
            if "crawler" in config_yaml:
                loaded.crawler = CrawlerSettings(**config_yaml["crawler"])

    prompts_path = loaded.BASE_DIR / "src" / "config" / "prompts.yaml"
    if prompts_path.exists():
        with prompts_path.open("r", encoding="utf-8") as f:
            loaded.prompts_yaml = yaml.safe_load(f) or {}

    return loaded


settings = load_settings()

