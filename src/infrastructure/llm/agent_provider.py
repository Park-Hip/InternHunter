from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.internhunter.llm.providers import GroqClient
from src.services.chat.tool_registry import get_all_tool_schemas
from src.config.settings import settings
from src.infrastructure.logging import get_logger
from src.core.models.chat import AgentResponse, Message

logger = get_logger(__name__)

class AgentLLMClient(GroqClient) :
    @retry(
        stop=stop_after_attempt(settings.config_yaml.get("crawler", {}).get("max_retries", 3)),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type(Exception)
    )
    def chat_completion(
        self,
        messages: List[Message],
        tools: List[dict] = None, 
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096, 
        stream: bool = False
    ) -> AgentResponse:
        try:
            if tools is None:
                tools = get_all_tool_schemas()

            api_messages = [m.model_dump(exclude_none=True) for m in messages]

            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=api_messages,
                tools=tools,
                temperature=temperature,
                stream=stream,
                max_tokens=max_tokens
            )
            raw_message = response.choices[0].message

            tool_calls = None
            if raw_message.tool_calls:
                tool_calls = [tc.model_dump() for tc in raw_message.tool_calls]

            return AgentResponse(
                content=raw_message.content,
                tool_calls=tool_calls,
                usage=response.usage.model_dump() if response.usage else None,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            logger.warning("AgentLLMClient failed to chat_completion", error=str(e))
            raise
            
        
