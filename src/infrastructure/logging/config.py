"""
Logging configuration using structlog.

Provides environment-aware logging with:
- JSON format for production (observability tools)
- Colored console format for development
- Context binding for request IDs, user info, etc.
"""

import sys
import structlog
from structlog.types import Processor
from typing import List
import logging


from src.config import settings


def get_processors(log_format: str) -> List[Processor]:
    """Get processors based on log format."""
    
    # Common processors for all environments
    common_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if log_format == "json":
        # Production: JSON format
        return common_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: Console format with colors
        return common_processors + [
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback
            )
        ]

def configure_logging() -> None:
    """
    Configure structlog for the application.
    
    Call this once at application startup (e.g., in main.py).
    """
    
    log_format = settings.LOG_FORMAT.lower()
    log_level = settings.LOG_LEVEL.upper()
    
    # Configure standard library logging for output
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )
    
    # Configure structlog
    structlog.configure(
        processors=get_processors(log_format),
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.logging, log_level, structlog.stdlib.logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
        
    Example:
        logger = get_logger(__name__)
        logger.info("Processing job", job_id=123, url="example.com")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs) -> None:
    """
    Bind context variables that will be included in all subsequent logs.
    
    Useful for adding request IDs, user IDs, etc. that should appear in all logs
    within a request/session.
    
    Args:
        **kwargs: Context key-value pairs
        
    Example:
        bind_context(request_id="abc-123", user_id=456)
        logger.info("User action")  # Automatically includes request_id, user_id
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
