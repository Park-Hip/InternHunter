"""
Custom processors for structlog.

Adds application-specific context and formatting to logs.
"""

import traceback
from typing import Any, Dict
from structlog.types import EventDict, WrappedLogger

from src.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add application context to every log entry.
    
    Includes: app name, version, environment
    """
    event_dict["app_name"] = settings.APP_NAME
    event_dict["app_version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def add_caller_info(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Add caller information (file, function, line) to logs.
    
    Only enabled in development for debugging.
    """
    if settings.ENVIRONMENT == "development":
        # Extract caller info from stack
        import inspect
        frame = inspect.currentframe()
        if frame:
            # Walk up the stack to find the actual caller (skip logging internals)
            for _ in range(10):
                frame = frame.f_back
                if frame and not frame.f_code.co_filename.endswith(('structlog', 'logging')):
                    event_dict["caller"] = {
                        "file": frame.f_code.co_filename.split('/')[-1],
                        "function": frame.f_code.co_name,
                        "line": frame.f_lineno
                    }
                    break
    return event_dict


def add_exception_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Enhanced exception formatting with full traceback.
    
    Extracts exception type, message, and formatted traceback.
    """
    exc_info = event_dict.get("exc_info")
    if exc_info:
        if isinstance(exc_info, tuple):
            exc_type, exc_value, exc_tb = exc_info
            event_dict["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value),
                "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            }
    return event_dict


def sanitize_sensitive_data(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Remove or mask sensitive data from logs.
    
    Prevents accidental logging of passwords, API keys, etc.
    """
    sensitive_keys = {"password", "api_key", "token", "secret", "authorization"}
    
    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: "***REDACTED***" if k.lower() in sensitive_keys else _sanitize(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, (list, tuple)):
            return [_sanitize(item) for item in obj]
        return obj
    
    return _sanitize(event_dict)
