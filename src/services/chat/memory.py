from typing import List

from src.core.models.chat import Message
from src.internhunter.common.logging import get_logger
from src.internhunter.storage.repositories.chat import MemoryRepository

logger = get_logger(__name__)


class ChatMemory:
    def __init__(self, session_id: str, limit: int = 10):
        self.session_id = session_id
        self.limit = limit
        self.repo = MemoryRepository()

    def load(self) -> List[Message]:
        messages = self.repo.load_messages(session_id=self.session_id, limit=self.limit)
        return messages

    def save(self, messages: List[Message]):
        self.repo.save_messages(session_id=self.session_id, messages=messages, limit=self.limit)


__all__ = ["ChatMemory"]

