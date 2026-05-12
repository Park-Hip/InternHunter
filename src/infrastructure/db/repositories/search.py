"""Compatibility shim for the legacy search repository import path."""

from src.internhunter.storage.repositories.search import SearchRepository
from src.internhunter.storage.repositories.search import SessionLocal  # noqa: F401

__all__ = ["SearchRepository", "SessionLocal"]
