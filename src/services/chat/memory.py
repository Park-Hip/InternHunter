from typing import List, Dict, Any
from sqlalchemy import select, func, and_, text
from typing import List

from src.infrastructure.db.session import  SessionLocal
from src.infrastructure.db.models import Base, ChatMessageDB, ChatSessionDB
from src.infrastructure.logging import get_logger
from src.core.models.chat import Message    
from src.infrastructure.db.repository import MemoryRepository

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

