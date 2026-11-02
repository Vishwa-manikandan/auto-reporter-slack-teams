"""Report which AI provider is actually in use.

The factory falls back to the mock provider when a cloud provider has no API
key. That is a reasonable default, but it must not be silent: the UI and the
report records show the effective provider so a stub report is never mistaken
for model output.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.config import settings

SUPPORTED_PROVIDERS = ("mock", "anthropic", "ollama", "openai")

_DEFAULTS = {
    "openai": ("gpt-4o-mini", "https://api.openai.com/v1"),
    "anthropic": ("claude-3-5-sonnet-20241022", "https://api.anthropic.com/v1"),
    "ollama": ("llama2", "http://localhost:11434/v1"),
}


def provider_status() -> Dict[str, Any]:
    requested = (settings.AI_PROVIDER or "mock").strip().lower()

    if requested not in SUPPORTED_PROVIDERS:
        return {
            "provider": "mock",
            "requested_provider": requested,
            "model": None,
            "base_url": None,
            "live": False,
            "configured": False,
            "note": f"Unknown AI_PROVIDER '{requested}'. Falling back to deterministic rules.",
        }

    if requested == "mock":
        return {
            "provider": "mock",
            "requested_provider": requested,
            "model": None,
            "base_url": None,
            "live": False,
            "configured": True,
            "note": "Deterministic rule extraction. No model calls are made.",
        }

    default_model, default_url = _DEFAULTS[requested]
    model = settings.AI_MODEL or default_model
    base_url = settings.AI_API_BASE_URL or default_url

    if requested == "ollama":
        return {
            "provider": "ollama",
            "requested_provider": requested,
            "model": model,
            "base_url": base_url,
            "live": True,
            "configured": True,
            "note": f"Local Ollama at {base_url}. Reports fail if the server is not running.",
        }

    configured = bool(settings.AI_API_KEY)
    if not configured:
        return {
            "provider": "mock",
            "requested_provider": requested,
            "model": model,
            "base_url": base_url,
            "live": False,
            "configured": False,
            "note": (
                f"AI_PROVIDER={requested} but AI_API_KEY is empty. "
                "Using deterministic rules instead of calling the API."
            ),
        }

    return {
        "provider": requested,
        "requested_provider": requested,
        "model": model,
        "base_url": base_url,
        "live": True,
        "configured": True,
        "note": f"Live {requested} calls using {model}.",
    }
