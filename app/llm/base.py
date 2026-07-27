"""
Abstract contracts for Large Language Model providers.

Every provider (OpenRouter, OpenAI, Gemini, Claude, Qwen, Ollama, etc.)
must implement this interface. The goal is to keep the rest of the
application completely provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Sequence

from app.llm.models import HealthStatus, LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """
    Base contract for all Large Language Model providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Unique provider identifier.

        Example:
            openrouter
            openai
            gemini
            ollama
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Currently configured model identifier.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def supported_models(self) -> Sequence[str]:
        """
        Models supported by this provider.
        """
        raise NotImplementedError

    @property
    def supports_streaming(self) -> bool:
        """
        Whether this provider supports token streaming.
        """
        return True

    @property
    def supports_tools(self) -> bool:
        """
        Whether this provider supports tool/function calling.
        """
        return False

    @property
    def supports_vision(self) -> bool:
        """
        Whether this provider supports image inputs.
        """
        return False

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate a complete response.
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the generated response.

        Yields:
            Text chunks from the model.
        """
        raise NotImplementedError

    async def stream(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the generated response (alias for stream_generate).

        Yields:
            Text chunks from the model.
        """
        async for chunk in self.stream_generate(request):
            yield chunk

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check provider health.

        Returns:
            HealthStatus describing provider availability.
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider='{self.provider_name}', "
            f"model='{self.model_name}')"
        )


BaseLLM = BaseLLMProvider