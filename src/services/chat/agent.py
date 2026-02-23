import mlflow
import os
import json
from groq import Groq
from dotenv import load_dotenv

from src.services.chat.memory import ChatMemory
from src.infrastructure.logging import get_logger
from src.services.chat.tool_registry import get_all_tool_schemas, execute_tool

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

def run_chat_agent(user_input: str, memory: ChatMemory, model: str = "openai/gpt-oss-120b") -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    if _mlflow_available:
        mlflow.groq.autolog()
        SYSTEM_PROMPT = mlflow.genai.load_prompt("prompts:/system_prompt/1").template
    else: 
        from src.infrastructure.llm.prompt.prompt import SYSTEM_PROMPT
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = memory.get_messages()
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    while True:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=get_all_tool_schemas()
            )
            assistant_msg = response.choices[0].message
            messages.append(assistant_msg)

            if assistant_msg.tool_calls:
                for tool_call in assistant_msg.tool_calls:
                    function_response = execute_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(function_response, default=str)
                    })
            else:
                memory.add_messages([
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": assistant_msg.content}
                ])
                return assistant_msg.content

        except Exception as e:
            logger.warning("Run chat agent failed", error=str(e))
            return f"Sorry, I encountered an error: {e}"