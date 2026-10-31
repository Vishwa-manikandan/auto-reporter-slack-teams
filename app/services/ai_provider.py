from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AIProvider(ABC):
    @abstractmethod
    async def summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        pass
    
    @abstractmethod
    async def extract_action_items(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass


class MockAIProvider(AIProvider):
    async def summarize_messages(self, messages: List[Dict[str, Any]]) -> str:
        return "Summary: Team activity shows ongoing development with some blockers and action items."
    
    async def extract_action_items(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return []


def get_ai_provider():
    from app.core.config import settings
    if settings.AI_PROVIDER == "mock":
        return MockAIProvider()
    return MockAIProvider()
