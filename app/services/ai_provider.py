import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.config import settings


class AIProviderError(Exception):
    pass


class AIProvider(ABC):
    @abstractmethod
    async def generate(self, messages: List[Dict[str, Any]], prompt: str, **kwargs) -> str:
        pass


class MockAIProvider(AIProvider):
    async def generate(self, messages: List[Dict[str, Any]], prompt: str, **kwargs) -> str:
        return json.dumps({
            "executive_summary": "No real AI configured; mock response.",
            "decisions": [],
            "action_items": [],
            "blockers": [],
            "project_updates": [],
            "important_discussions": [],
            "follow_ups": [],
            "source_references": []
        })


class OpenAIProvider(AIProvider):
    def __init__(self):
        self.api_key = getattr(settings, "AI_API_KEY", None) or os.getenv("AI_API_KEY")
        self.model = getattr(settings, "AI_MODEL", None) or os.getenv("AI_MODEL", "gpt-4o-mini")
        self.base_url = getattr(settings, "AI_API_BASE_URL", None) or os.getenv("AI_API_BASE_URL", "https://api.openai.com/v1")
        self.timeout = int(getattr(settings, "AI_REQUEST_TIMEOUT", None) or os.getenv("AI_REQUEST_TIMEOUT", "60"))

    async def generate(self, messages: List[Dict[str, Any]], prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY not configured")
        try:
            import httpx

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": prompt}] + [{"role": "user", "content": json.dumps(messages[-100:])}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code >= 400:
                    raise AIProviderError(f"AI API error {resp.status_code}")
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except AIProviderError:
            raise
        except Exception as e:
            raise AIProviderError(str(e))


class AIProviderFactory:
    @staticmethod
    def create(provider: Optional[str] = None) -> AIProvider:
        provider = provider or getattr(settings, "AI_PROVIDER", None) or os.getenv("AI_PROVIDER", "mock")
        provider = provider.lower()
        if provider in ("openai", "openrouter", "anthropic", "ollama"):
            # For this implementation, use OpenAI-compatible client
            if provider == "openai" or os.getenv("AI_API_KEY"):
                try:
                    return OpenAIProvider()
                except Exception:
                    pass
        if provider == "mock":
            return MockAIProvider()
        # Default to OpenAI if key exists, else mock
        if os.getenv("AI_API_KEY"):
            try:
                return OpenAIProvider()
            except Exception:
                pass
        return MockAIProvider()
