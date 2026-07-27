"""AI Provider Registry for MantraSetu AgentOS.

This module provides thread-safe registration, resolution, unregistration, and diagnostic
health checking of AI provider implementations without creating instances or executing inference commands.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.ai.base import AIProviderError, BaseAIProvider


class AIProviderRegistry:
    """Thread-safe registry for registering and resolving AI provider implementations.

    Responsibility:
        Stores and resolves BaseAIProvider instances by string keys.
        Does not instantiate providers, parse environment variables, or execute inference.
    """

    def __init__(self) -> None:
        """Initialize AIProviderRegistry with internal storage map and thread-safe lock."""
        self._providers: dict[str, BaseAIProvider] = {}
        self._lock = asyncio.Lock()

    def _normalize_key(self, provider_type: str) -> str:
        """Normalize provider key representation.

        Args:
            provider_type: Provider string identifier.

        Returns:
            str: Normalized string key.
        """
        return provider_type.lower()

    async def register(
        self,
        provider_type: str,
        provider: BaseAIProvider,
    ) -> None:
        """Register a BaseAIProvider instance for a provider key.

        Args:
            provider_type: Provider string identifier.
            provider: BaseAIProvider instance to register.

        Raises:
            AIProviderError: If the provider key is already registered.
        """
        key = self._normalize_key(provider_type)
        async with self._lock:
            if key in self._providers:
                raise AIProviderError(f"AI provider '{provider_type}' is already registered.")
            self._providers[key] = provider

    async def unregister(self, provider_type: str) -> None:
        """Unregister a provider instance by provider key.

        Args:
            provider_type: Provider string identifier.

        Raises:
            AIProviderError: If the provider key is not found.
        """
        key = self._normalize_key(provider_type)
        async with self._lock:
            if key not in self._providers:
                raise AIProviderError(f"AI provider '{provider_type}' is not registered.")
            del self._providers[key]

    async def get(self, provider_type: str) -> BaseAIProvider:
        """Resolve a registered BaseAIProvider instance by provider key.

        Args:
            provider_type: Provider string identifier.

        Returns:
            BaseAIProvider: Registered provider instance.

        Raises:
            AIProviderError: If the provider key is not found.
        """
        key = self._normalize_key(provider_type)
        async with self._lock:
            provider = self._providers.get(key)
            if not provider:
                raise AIProviderError(f"AI provider '{provider_type}' is not registered.")
            return provider

    async def contains(self, provider_type: str) -> bool:
        """Check if a provider key is registered in the registry.

        Args:
            provider_type: Provider string identifier.

        Returns:
            bool: True if registered, False otherwise.
        """
        key = self._normalize_key(provider_type)
        async with self._lock:
            return key in self._providers

    async def list_providers(self) -> tuple[str, ...]:
        """List all registered provider keys.

        Returns:
            tuple[str, ...]: Immutable tuple of registered provider keys.
        """
        async with self._lock:
            return tuple(self._providers.keys())

    async def clear(self) -> None:
        """Clear all registered provider instances from the registry."""
        async with self._lock:
            self._providers.clear()

    async def health_check(self) -> dict[str, object]:
        """Run health check probes across all registered provider instances.

        Returns:
            dict[str, object]: Dictionary mapping provider key strings to status dictionaries.
        """
        async with self._lock:
            providers_snapshot = list(self._providers.items())

        results: dict[str, object] = {}
        for key, provider in providers_snapshot:
            try:
                status = await provider.health_check()
                results[key] = status
            except Exception as e:
                results[key] = {
                    "healthy": False,
                    "provider": key,
                    "message": f"Health probe failed: {str(e)}",
                }

        return results
