from src.internhunter.common.logging import (
    configure_logging as new_configure_logging,
    get_logger as new_get_logger,
)
from src.internhunter.config.settings import settings as new_settings
from src.infrastructure.logging import (
    configure_logging as legacy_configure_logging,
    get_logger as legacy_get_logger,
)
from src.infrastructure.logging.config import (
    configure_logging as legacy_config_configure_logging,
    get_logger as legacy_config_get_logger,
)
from src.config.settings import settings as legacy_settings


def test_foundation_modules_import():
    logger = new_get_logger(__name__)

    assert logger is not None
    assert new_settings is legacy_settings
    assert new_settings.APP_NAME == "job-finder"
    assert isinstance(new_settings.search_urls, list)
    assert len(new_settings.search_urls) == 2
    assert legacy_get_logger is new_get_logger
    assert legacy_config_get_logger is new_get_logger
    assert legacy_configure_logging is new_configure_logging
    assert legacy_config_configure_logging is new_configure_logging
