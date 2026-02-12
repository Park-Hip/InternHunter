"""
Example demonstrating the new structlog logging system.

Run this to see both console and JSON output formats.
"""

import sys
sys.path.insert(0, 'd:/Data Science Project/job_finder')

from src.infrastructure.logging import configure_logging, get_logger, bind_context

# Initialize logging (call once at startup)
configure_logging()

# Get logger
logger = get_logger(__name__)

def demonstrate_logging():
    """Demonstrate various logging features."""
    
    # Basic logging
    logger.info("Application started")
    logger.debug("Debug information", module="example", version="1.0")
    
    # Structured logging with context
    logger.info(
        "Processing job",
        job_id=12345,
        url="https://example.com/job/12345",
        company="TechCorp",
        status="pending"
    )
    
    # Bind context (will appear in all subsequent logs)
    bind_context(request_id="req-abc-123", user_id=456)
    
    logger.info("User action", action="view_job", job_id=12345)
    logger.info("Another action", action="apply", job_id=67890)
    # Both logs above will include request_id and user_id
    
    # Warning and error logs
    logger.warning(
        "Rate limit approaching",
        current_requests=95,
        limit=100,
        remaining=5
    )
    
    # Error with exception
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.error(
            "Calculation failed",
            operation="divide",
            numerator=10,
            denominator=0,
            exc_info=True  # Include exception traceback
        )
    
    # Success log
    logger.info(
        "Job saved successfully",
        job_id=12345,
        duration_ms=245,
        database="jobs.db"
    )

if __name__ == "__main__":
    print("=" * 60)
    print("CONSOLE FORMAT (Development)")
    print("=" * 60)
    demonstrate_logging()
    
    print("\n" + "=" * 60)
    print("To see JSON format, set LOG_FORMAT=json in .env")
    print("=" * 60)
