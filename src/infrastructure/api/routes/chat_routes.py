from fastapi import HTTPException, APIRouter
from src.core.models import ChatRequest, ChatResponse
from src.internhunter.chat.agent import run_chat_agent
from src.internhunter.common.logging import get_logger
from src.internhunter.storage.repositories.chat import MemoryRepository


logger = get_logger(__name__)

router = APIRouter()

@router.get("/")
def root():
    return {"message": "Welcome to job-finder"}

@router.post("/api/chat")
def chat(request: ChatRequest) -> ChatResponse:
    try:
        response = run_chat_agent(request)
        return response
    except Exception as e:
        logger.error("Chat with agent failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error occurred.")

@router.get("/api/chat/sessions/{session_id}")
def fetch_chat_history(session_id: str):
    try:
        mem_repo = MemoryRepository()
        chat_history = mem_repo.load_messages(session_id)

        return {"chat_history": chat_history}
    except Exception as e:
        logger.warning("Feftch chat histrory failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error occurred.")

@router.get("/api/chat/users/{user_id}/sessions")
def get_sessions(user_id):
    try:
        mem_repo = MemoryRepository()
        sessions = mem_repo.get_user_sessions(user_id)
    except Exception as e:
        logger.warning("Failed to get user sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error occurred.")


@router.delete("/api/chat/sessions/{session_id}")
def delete_session(session_id: str):
    try:
        mem_repo = MemoryRepository()
        mem_repo.delete_session(session_id)
    except Exception as e:
        logger.error("Delete session failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error occurred.")
