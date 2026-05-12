import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
from infrastructure.prefect.flows import run_production_pipeline
from internhunter.config.settings import settings
from internhunter.common.logging import configure_logging

async def main():
    configure_logging()
    # Test with DS_URL
    await run_production_pipeline(settings.DS_URL)

if __name__ == "__main__":
    asyncio.run(main())
