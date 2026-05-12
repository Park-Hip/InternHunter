from src.internhunter.common.logging import get_logger
from src.internhunter.config.settings import settings


def test_foundation_modules_import():
    logger = get_logger(__name__)

    assert logger is not None
    assert settings.APP_NAME == "internhunter"
    assert isinstance(settings.search_urls, list)
    assert len(settings.search_urls) == 2

