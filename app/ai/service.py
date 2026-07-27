"""AI Subsystem Service Facade for MantraSetu AgentOS.

This module provides AIService as the primary public entry point for the AI subsystem,
coordinating provider access, completion generation, streaming, and health checks via AIFactory
and AIProviderRegistry without performing HTTP requests or parsing provider payloads directly.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.ai.base import (
    AIInitializationError,
    BaseAIProvider,
)
from app.ai.factory import AIFactory
from app.ai.models import (
    AIRequest,
    AIResponse,
)
from app.ai.registry import AIProviderRegistry


class AIService:
    """Public facade service coordinating AI inference provider backends.

    Responsibility:
        Exposes a clean subsystem facade API for AI inference. Delegates provider creation,
        resolution, and shutdown to AIFactory, delegates inference and streaming execution
        to resolved BaseAIProvider instances, and delegates diagnostic probes to AIProviderRegistry.
    """

    def __init__(
        self,
        factory: AIFactory,
        registry: AIProviderRegistry | None = None,
        default_provider: str = "mock",
    ) -> None:
        """Initialize AIService with injected factory and registry dependencies.

        Args:
            factory: AIFactory instance for provider instantiation and lifecycle management.
            registry: Optional AIProviderRegistry instance for registry queries and health probes.
            default_provider: Default provider string key used when request provider is omitted.
        """
        self._factory = factory
        self._registry = registry
        self._default_provider = default_provider
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the AI service has been initialized.

        Raises:
            AIInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AIInitializationError(
                "AIService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize the AI service and ensure the default provider is available."""
        if self._initialized:
            return

        # Pre-initialize default provider instance
        await self._factory.get_or_create(self._default_provider)
        self._initialized = True

    async def close(self) -> None:
        """Close all active providers and release allocated subsystem resources."""
        await self._factory.shutdown()
        self._initialized = False

    async def get_provider(
        self,
        provider_type: str,
    ) -> BaseAIProvider:
        """Resolve or instantiate a BaseAIProvider backend via AIFactory.

        Args:
            provider_type: Target provider string identifier.

        Returns:
            BaseAIProvider: Initialized provider instance.

        Raises:
            AIInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        return await self._factory.get_or_create(provider_type)

    async def available_providers(self) -> tuple[str, ...]:
        """List all currently registered active AI providers.

        Returns:
            tuple[str, ...]: Immutable tuple of provider identifier keys.

        Raises:
            AIInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        if self._registry:
            return await self._registry.list_providers()
        return (self._default_provider,)

    async def generate(self, request: AIRequest) -> AIResponse:
        """Delegate text/chat completion generation to the requested or default provider backend.

        Args:
            request: Provider-independent AIRequest payload model.

        Returns:
            AIResponse: Domain AIResponse output model.

        Raises:
            AIInitializationError: If service is uninitialized.
            AIProviderError: If execution fails at the provider layer.
        """
        self._require_initialized()
        provider = await self._factory.get_or_create(self._default_provider)
        return await provider.generate(request)

    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Delegate streaming text/chat completion generation to the requested or default provider backend.

        Args:
            request: Provider-independent AIRequest payload model.

        Yields:
            str | dict[str, object]: Incremental token or delta data.

        Raises:
            AIInitializationError: If service is uninitialized.
            AIProviderError: If streaming fails at the provider layer.
        """
        self._require_initialized()
        provider = await self._factory.get_or_create(self._default_provider)
        async for chunk in provider.stream(request):
            yield chunk

    async def health_check(self) -> dict[str, object]:
        """Delegate operational health check probes to AIProviderRegistry or default provider.

        Returns:
            dict[str, object]: Dictionary mapping provider names to diagnostic results.

        Raises:
            AIInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        if self._registry:
            return await self._registry.health_check()

        provider = await self._factory.get_or_create(self._default_provider)
        return {self._default_provider: await provider.health_check()}
