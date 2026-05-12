import asyncio
from src.infrastructure.prefect.flows import run_production_pipeline
from src.config.settings import settings
from src.infrastructure.logging import configure_logging

async def main():
    configure_logging()
    # Test with DS_URL
    await run_production_pipeline(settings.DS_URL)

if __name__ == "__main__":
    asyncio.run(main())
