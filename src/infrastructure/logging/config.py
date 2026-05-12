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


from src.config.settings import settings


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
    
    log_cfg = settings.config_yaml.get("logging", {})
    log_format = log_cfg.get("format", "console").lower()
    log_level = log_cfg.get("level", "INFO").upper()
    
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
    
    This is ADDITIVE — it merges new variables with existing context.
    Use reset_context() if you need to clear everything first.
    
    Args:
        **kwargs: Context key-value pairs
        
    Example:
        bind_context(run_id="abc-123")
        bind_context(phase="extract")  # run_id is preserved
        logger.info("Action")  # Includes both run_id and phase
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def reset_context(**kwargs) -> None:
    """
    Clear ALL bound context variables, then optionally set new ones.
    
    Use this at the start of a new pipeline run to ensure a clean slate.
    
    Args:
        **kwargs: Optional new context to bind after clearing.
    """
    structlog.contextvars.clear_contextvars()
    if kwargs:
        structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
