from typing import List, Dict, Any

class ChatMemory:
    def __init__(self, history: List[Dict[str, Any]] = None, limit: int = 10):
        self.history = history if history is not None else []
        self.limit = limit

    def add_messages(self, messages: List[Dict[str, Any]]):
        self.history.extend(messages)

        if len(self.history) > self.limit:
            self.history = self.history[-self.limit:]

    def get_messages(self) -> List[Dict[str, Any]]:
        return self.history