"""Mock AI Provider implementation for MantraSetu AgentOS.

This module provides MockAIProvider implementing BaseAIProvider for deterministic testing,
unit test suites, and fallback environments without network connections or external API SDKs.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from uuid import UUID, uuid4

from app.ai.base import AIInitializationError, BaseAIProvider
from app.ai.models import (
    AIRequest,
    AIResponse,
    AIStatus,
    TokenUsage,
)


class MockAIProvider(BaseAIProvider):
    """Mock AI Provider implementing BaseAIProvider contract.

    Responsibility:
        Provides deterministic inference responses and streaming chunks for unit testing,
        local development, and offline evaluation without external network calls or API keys.
    """

    def __init__(self, name: str = "mock") -> None:
        """Initialize MockAIProvider.

        Args:
            name: Optional provider identifier name string.
        """
        self._name = name
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify provider has been initialized.

        Raises:
            AIInitializationError: If provider is uninitialized.
        """
        if not self._initialized:
            raise AIInitializationError(
                f"MockAIProvider '{self._name}' is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize mock provider state."""
        self._initialized = True

    async def close(self) -> None:
        """Close mock provider state."""
        self._initialized = False

    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate a deterministic mock AIResponse model.

        Args:
            request: AIRequest payload model.

        Returns:
            AIResponse: Deterministic AI response model.

        Raises:
            AIInitializationError: If provider is uninitialized.
        """
        self._require_initialized()

        output_text = (
            f"Mock response generated for request {request.request_id} using model '{request.model}'."
        )

        return AIResponse(
            request_id=request.request_id,
            content=output_text,
            model=request.model or self._name,
            status=AIStatus.SUCCESS,
            usage=TokenUsage(input_tokens=12, output_tokens=18, total_tokens=30),
            execution_time_ms=1.5,
        )

    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Generate streaming token delta chunks deterministically.

        Args:
            request: AIRequest payload model.

        Yields:
            str | dict[str, object]: Incremental token or delta data.

        Raises:
            AIInitializationError: If provider is uninitialized.
        """
        self._require_initialized()

        tokens = ["Mock ", "streaming ", "response ", "completed."]
        for i, token in enumerate(tokens):
            await asyncio.sleep(0.01)
            yield token

    async def health_check(self) -> dict[str, object]:
        """Check operational health status of the mock provider.

        Returns:
            dict[str, object]: Diagnostic health status dictionary.
        """
        return {
            "healthy": self._initialized,
            "provider": self._name,
            "latency_ms": 0.5,
            "message": "Mock AI provider operational."
            if self._initialized
            else "Mock AI provider uninitialized.",
        }
