import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.services.chat.agent import run_chat_agent
from src.services.chat.memory import ChatMemory
from src.internhunter.common.logging import configure_logging

memory = ChatMemory()

if __name__ == "__main__":
    configure_logging()
    while True:
        user_input = input("You: ")

        if user_input.lower().strip() == 'exit':
            break
        
        response = run_chat_agent(user_input=user_input, memory=memory)
        print(f"AI: {response}")
