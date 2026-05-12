from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.infrastructure.db.repositories.search import SearchRepository
from src.infrastructure.db.repositories.chat import ChatRepository
from src.infrastructure.llm.router import llm_router
from src.services.chat.tool_registry import register_tool
from src.internhunter.embeddings.embedder import Embedder
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)
search_repo = SearchRepository()
chat_repo = ChatRepository()
embedder = Embedder()

# --- Text-to-SQL Tool ---

class SQLSearchArgs(BaseModel):
    query: str = Field(..., description="The natural language question to translate into SQL (e.g., 'What are the top 5 skills for AI engineers?').")

@register_tool(
    name="search_jobs_sql",
    description="Use this to perform analytical queries or complex filtering on the job database using natural language.",
    args_schema=SQLSearchArgs
)
def execute_sql_search(query: str) -> str:
    try:
        from langchain.chains import create_sql_query_chain
        from langchain_community.utilities import SQLDatabase
        from src.internhunter.storage.session import engine

        db = SQLDatabase(engine)

        # We use the router's primary LLM to generate the SQL
        llm = llm_router.primary_provider.llm
        chain = create_sql_query_chain(llm, db)
        sql_query = chain.invoke({"question": query})
        
        # Clean the SQL query (remove markdown formatting if any)
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        
        # Execute the query safely
        result = db.run(sql_query)
        return f"Query: {sql_query}\nResult: {result}"
    except Exception as e:
        logger.error("execute_sql_search failed", error=str(e))
        return f"Error executing SQL search: {str(e)}"

# --- Resume RAG Tool ---

class MatchResumeArgs(BaseModel):
    user_id: str = Field(..., description="The unique ID of the user whose resume should be used for matching.")
    limit: int = Field(5, description="The maximum number of matches to return.")

@register_tool(
    name="match_jobs_resume",
    description="Finds the most relevant job postings for a user based on their uploaded resume using semantic similarity.",
    args_schema=MatchResumeArgs
)
def execute_match_resume(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    try:
        profile = chat_repo.get_user_profile(user_id)
        if not profile or not profile.get("resume_embedding"):
            return [{"error": "No resume found for this user. Please upload a resume first."}]
        
        results = search_repo.search_jobs_by_similarity(profile["resume_embedding"], limit=limit)
        return results
    except Exception as e:
        logger.error("execute_match_resume failed", error=str(e))
        return [{"error": f"Failed to match resume: {str(e)}"}]

# --- Resume Upload Tool ---

class UploadResumeArgs(BaseModel):
    user_id: str = Field(..., description="The unique ID to associate with this resume.")
    resume_text: str = Field(..., description="The full text content of the resume.")

@register_tool(
    name="upload_resume",
    description="Uploads and processes a user's resume for future job matching.",
    args_schema=UploadResumeArgs
)
def execute_upload_resume(user_id: str, resume_text: str) -> str:
    try:
        embedding = embedder.generate_embedding(resume_text)
        if chat_repo.save_user_profile(user_id, resume_text, embedding):
            return "Resume successfully uploaded and vectorized. You can now ask me to match jobs based on your profile!"
        return "Failed to save resume to the database."
    except Exception as e:
        logger.error("execute_upload_resume failed", error=str(e))
        return f"Error uploading resume: {str(e)}"
