"""Factory for constructing LLM provider instances."""

from __future__ import annotations

from typing import Any

from app.llm.base import BaseLLM
from app.llm.config import LLMSettings, get_llm_settings
from app.llm.exceptions import LLMConfigurationError
from app.llm.providers.qwen import QwenLLM


class LLMFactory:
    """Create provider instances from runtime configuration."""

    _providers = {
        "qwen": QwenLLM,
    }

    @classmethod
    def create(cls, settings: LLMSettings | None = None, **kwargs: Any) -> BaseLLM:
        """Return a configured provider instance."""
        resolved_settings = settings or get_llm_settings()
        provider_key = resolved_settings.provider.strip().lower()
        provider_class = cls._providers.get(provider_key)
        if provider_class is None:
            raise LLMConfigurationError(f"Unsupported LLM provider: {resolved_settings.provider}")
        return provider_class(settings=resolved_settings, **kwargs)


def get_llm() -> BaseLLM:
    """Convenience accessor for application code."""
    return LLMFactory.create()
