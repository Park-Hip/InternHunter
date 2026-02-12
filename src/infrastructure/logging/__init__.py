"""
Logging module for Job Finder application.

Provides structured logging with environment-aware formatting.

Usage:
    from src.infrastructure.logging import get_logger, configure_logging
    
    # Initialize once at startup
    configure_logging()
    
    # Get logger in any module
    logger = get_logger(__name__)
    logger.info("Processing job", job_id=123, url="example.com")
    
    # Bind context for request/session
    from src.infrastructure.logging import bind_context
    bind_context(request_id="abc-123", user_id=456)
"""

from src.infrastructure.logging.config import (
    configure_logging,
    get_logger,
    bind_context,
    clear_context
)

__all__ = [
    "configure_logging",
    "get_logger",
    "bind_context",
    "clear_context"
]
