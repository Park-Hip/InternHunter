from typing import List, Dict, Any, Optional

from sqlalchemy import select

from src.internhunter.storage.session import SessionLocal
from src.internhunter.storage.models import ChatSessionDB, ChatMessageDB, UserProfileDB
from src.core.models.chat import Message
from src.internhunter.common.logging import get_logger

logger = get_logger(__name__)


class ChatRepository:
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as session:
            try:
                statement = select(UserProfileDB).where(UserProfileDB.user_id == user_id)
                profile = session.execute(statement).scalar_one_or_none()
                if profile:
                    return {
                        "user_id": profile.user_id,
                        "resume_text": profile.resume_text,
                        "resume_embedding": profile.resume_embedding,
                    }
                return None
            except Exception as e:
                logger.error(f"Failed to get user profile: {e}")
                return None

    def save_user_profile(self, user_id: str, resume_text: str, embedding: List[float]) -> bool:
        with SessionLocal() as session:
            try:
                statement = select(UserProfileDB).where(UserProfileDB.user_id == user_id)
                profile = session.execute(statement).scalar_one_or_none()
                if profile:
                    profile.resume_text = resume_text
                    profile.resume_embedding = embedding
                else:
                    profile = UserProfileDB(
                        user_id=user_id,
                        resume_text=resume_text,
                        resume_embedding=embedding,
                    )
                    session.add(profile)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to save user profile: {e}")
                return False

    def load_messages(self, session_id: str, limit: int = 10) -> List[Message]:
        with SessionLocal() as session:
            try:
                statement = (
                    select(ChatMessageDB)
                    .where(ChatMessageDB.session_id == session_id)
                    .order_by(ChatMessageDB.created_at.desc())
                    .limit(limit)
                )
                result = session.execute(statement).scalars().all()
                messages = reversed(result)
                return [
                    Message(
                        role=m.role,
                        content=m.content,
                        tool_calls=m.tool_calls,
                        tool_call_id=m.tool_call_id,
                    )
                    for m in messages
                ]
            except Exception as e:
                logger.error("Failed to load messages from ChatMessageDB", error=str(e))
                raise

    def save_messages(self, session_id: str, messages: List[Message], limit: int = 10):
        # TODO: verify whether chat history persistence should stay in storage or move to a dedicated memory layer.
        with SessionLocal() as session:
            try:
                statement = select(ChatSessionDB).where(ChatSessionDB.id == session_id)
                chat_session = session.execute(statement).scalar_one_or_none()
                if not chat_session:
                    user_id = None
                    for m in messages:
                        if m.user_id:
                            user_id = m.user_id
                            break
                    chat_session = ChatSessionDB(id=session_id, user_id=user_id)
                    session.add(chat_session)
                    session.commit()

                if len(messages) > limit:
                    messages = messages[-limit:]

                for message in messages:
                    new_message = ChatMessageDB(
                        role=message.role,
                        content=message.content,
                        user_id=message.user_id,
                        session_id=session_id,
                        tokens_used=message.tokens_used,
                        tool_calls=message.tool_calls,
                        tool_call_id=message.tool_call_id,
                    )
                    session.add(new_message)
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error("Failed save messages to ChatMessageDB", error=str(e))

    def get_user_sessions(self, user_id: str) -> List[dict]:
        with SessionLocal() as session:
            try:
                statement = select(ChatSessionDB).where(ChatSessionDB.user_id == user_id)
                chat_sessions = session.execute(statement).scalars().all()
                return [
                    {
                        "session_id": s.id,
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in chat_sessions
                ]
            except Exception as e:
                logger.error("Failed to get_user_sessions", error=str(e))
                raise

    def delete_session(self, session_id: str) -> bool:
        from sqlalchemy import delete

        with SessionLocal() as session:
            try:
                statement = delete(ChatSessionDB).where(ChatSessionDB.id == session_id)
                session.execute(statement)
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error("delete_session failed", error=str(e))
                raise

# TODO: verify whether chat history persistence should remain under a "memory" name
# or be renamed everywhere to "chat repository" in a later refactor.
MemoryRepository = ChatRepository


__all__ = ["ChatRepository", "MemoryRepository"]
