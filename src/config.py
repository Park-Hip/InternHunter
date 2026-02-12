import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: SecretStr
    GROQ_API_KEY: SecretStr
    DB_PATH: str = "jobs.db"
    DB_URL: str = "sqlite:///./job-finder.db"
    # URL: str = "https://www.topcv.vn/tim-viec-lam-ai-engineer?sort=new&type_keyword=1&saturday_status=0&sba=1"
    URL: str = "https://www.topcv.vn/tim-viec-lam-ai-engineer?sba=1"

    MAX_RETRIES: int = 3
    RATE_LIMIT_RPM: int = 20

    # Logging Configuration
    LOG_FORMAT: str = "console"  # "console" or "json"
    LOG_LEVEL: str = "INFO"
    
    # Application Metadata
    APP_NAME: str = "job-finder"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"  # "development" or "production"

    MLFLOW_TRACKING_URI: str = "sqlite:///mlflow.db"
    MLFLOW_EXPERIMENT: str = "job-finder"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" 
    )

settings = Settings()