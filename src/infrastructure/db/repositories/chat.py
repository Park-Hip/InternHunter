"""Compatibility shim for the legacy chat repository import path."""

from src.internhunter.storage.repositories.chat import ChatRepository
from src.internhunter.storage.repositories.chat import SessionLocal  # noqa: F401

__all__ = ["ChatRepository", "SessionLocal"]
