class JobFinderError(Exception):
    """Base exception for the application."""
    pass

class LLMGenerationError(JobFinderError):
    """Raised when LLM fails to generate content."""
    pass

class DatabaseError(JobFinderError):
    """Raised for DB operations."""
    pass
