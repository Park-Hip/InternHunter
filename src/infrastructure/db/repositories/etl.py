"""Compatibility shim for the legacy ETL repository import path."""

from src.internhunter.storage.repositories.etl import ETLRepository, etl_repo
from src.internhunter.storage.repositories.etl import SessionLocal  # noqa: F401

__all__ = ["ETLRepository", "etl_repo", "SessionLocal"]
