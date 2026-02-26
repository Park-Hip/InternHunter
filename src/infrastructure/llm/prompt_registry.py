import mlflow
import sys
import os
from dotenv import load_dotenv
from typing import Any

from src.infrastructure.logging import get_logger, configure_logging
from src.config import settings

logger = get_logger(__name__)

load_dotenv()

mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
mlflow.set_experiment(settings.MLFLOW_EXPERIMENT)

from mlflow.tracking import MlflowClient

PROMPTS_DIR = settings.BASE_DIR / "src" / "infrastructure" / "llm" / "prompts"

def load_prompt_from_file(filename: str) -> str:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

def register_prompt(prompt_name: str, use_case: str, template: str, commit_message: str = "Update") -> Any:
    logger.info("Attempting to register prompt")

    try:
        prompt_info = mlflow.genai.register_prompt(
            name=prompt_name,
            template=template,
            commit_message=commit_message,
            tags={
                "author": "Park-Hip",
                "language": "en",
                "use_case": use_case,
            }
        )

        mlflow.genai.set_prompt_alias(name=prompt_name, alias="production", version=prompt_info.version)
        
        logger.info("Prompt successfully registered and set to @production alias")
        logger.info("Prompt details", name=prompt_info.name, version=prompt_info.version)
        return prompt_info

    except Exception as e:
        logger.error("Prompt registration failed", error=str(e), exc_info=True)
        raise e

def sync_prompts_to_mlflow():
    """Iterate through prompt files and sync them to MLflow."""
    prompts_to_sync = {
        "job_processor": "extraction",
        "agent_system": "agent_assistant"
    }
    
    for name, use_case in prompts_to_sync.items():
        template = load_prompt_from_file(f"{name}.txt")
        
        register_prompt(
            prompt_name=name,
            use_case=use_case,
            template=template,
            commit_message="Automated sync from git"
        )

if __name__ == "__main__":
    sync_prompts_to_mlflow()