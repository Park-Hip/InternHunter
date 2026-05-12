import mlflow
import os
import json
from groq import Groq
from dotenv import load_dotenv

from src.internhunter.chat.memory import ChatMemory
from src.infrastructure.logging import get_logger
from src.internhunter.chat.tool_registry import get_all_tool_schemas, execute_tool
from src.core.models.chat import ChatResponse, ToolCallInfo, Message, ChatRequest
from src.infrastructure.llm.agent_provider import AgentLLMClient
from src.config.settings import settings
from src.services.chat import tools # Trigger registration

logger = get_logger(__name__)
load_dotenv()

try:
    if os.getenv("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    if os.getenv("MLFLOW_EXPERIMENT"):
        mlflow.set_experiment(os.environ["MLFLOW_EXPERIMENT"])
    
    _mlflow_available = True

except ImportError:
    _mlflow_available = False
    logger.info("MLflow not available, skipping autolog setup.")

def run_chat_agent(
        request: ChatRequest, 
        max_iteration: int = None
    ) -> ChatResponse:
    if max_iteration is None:
        max_iteration = settings.config_yaml.get("agent", {}).get("max_iterations", 5)
    memory = ChatMemory(session_id=request.session_id)
    llm = AgentLLMClient()

    if _mlflow_available:
        mlflow.groq.autolog()
        try:
            SYSTEM_PROMPT = mlflow.genai.load_prompt("prompts:/agent_system@production").template
        except Exception:
            SYSTEM_PROMPT = settings.get_prompt("agent_system")
    else:
        SYSTEM_PROMPT = settings.get_prompt("agent_system")
    
    old_messages = memory.load()
    user_message = [Message(
        role = "user",
        content = request.user_message,
        session_id = request.session_id,
        user_id = request.user_id,
        # tokens_used
    )]
    if len(old_messages) == 0:
        system_message = [Message(
            role = 'system',
            content = SYSTEM_PROMPT,
            session_id = request.session_id,
            user_id = request.user_id,
        )]
        messages = system_message + old_messages + user_message
    else:
        messages = old_messages + user_message

    tool_calls_made = []

    for i in range(max_iteration):
        try: 
            agent_response = llm.chat_completion(messages=messages)

            assistant_msg = Message(
                role="assistant",
                content=agent_response.content,
                tool_calls=agent_response.tool_calls,
                session_id=request.session_id,
                user_id=request.user_id,
                tokens_used=agent_response.usage.get("completion_tokens") if agent_response.usage else None
            )
            messages.append(assistant_msg)
            
            if not agent_response.tool_calls:
                memory.save(messages) # Save everything to DB
                return ChatResponse(
                    user_id=request.user_id,
                    session_id=request.session_id,
                    tool_calls_made=tool_calls_made,
                    message=agent_response.content or ""
                )

            for tool_call in agent_response.tool_calls:
                tool_name = tool_call.get("function", {}).get("name")
                
                try:
                    arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                except json.JSONDecodeError:
                    arguments = {}
  
                tool_calls_made.append(ToolCallInfo(tool_name=tool_name, arguments=arguments))

                tool_result = execute_tool(tool_name, arguments)

                tool_msg = Message(
                    role="tool",
                    content=json.dumps(tool_result, default=str), # Convert dict to string
                    tool_call_id=tool_call.get("id"), # EXTREMELY IMPORTANT: Link it back!
                    session_id=request.session_id,
                    user_id=request.user_id
                )

                messages.append(tool_msg)

        except Exception as e:
            logger.warning("Run chat agent failed", error=str(e))
            raise e

    final_fallback_msg = Message(
        role="assistant",
        content="I have exceeded my maximum allowed steps and must stop. Please try asking again.",
        session_id=request.session_id,
        user_id=request.user_id
    )
    messages.append(final_fallback_msg)
    memory.save(messages)
    
    return ChatResponse(
        user_id=request.user_id,
        session_id=request.session_id,
        tool_calls_made=tool_calls_made,
        message=final_fallback_msg.content
    )
