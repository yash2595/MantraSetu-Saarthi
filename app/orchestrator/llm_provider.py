"""LLM Provider interfaces and standard implementations for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, AsyncIterator

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_contracts import ILLMProviderBridge
from app.orchestrator.orchestrator_models import (
    OrchestratorContext,
    ProviderResponse,
    ProviderType,
    StreamingChunk,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MockLLMProvider"
_COMPONENT_VERSION = "4.1"


class MockLLMProvider(ILLMProviderBridge):
    """Deterministic mock LLM provider for local execution and enterprise unit testing."""

    def __init__(self, provider_type: ProviderType = ProviderType.MOCK) -> None:
        self.provider_type = provider_type
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._generations_count = 0

    async def generate(self, context: OrchestratorContext) -> ProviderResponse:
        """Generate a deterministic ProviderResponse model."""
        with self._lock:
            self._generations_count += 1

        user_text = context.request.user_message
        resp_text = f"I am MantraSetu AI (Provider: {self.provider_type.value}). Processed request: '{user_text}'."

        return ProviderResponse(
            provider_type=self.provider_type,
            text=resp_text,
            usage_tokens=42,
            latency_ms=1.5,
        )

    async def stream(self, context: OrchestratorContext) -> AsyncIterator[StreamingChunk]:
        """Stream response chunks incrementally."""
        full_res = await self.generate(context)
        words = full_res.text.split(" ")
        for i, w in enumerate(words):
            is_last = i == (len(words) - 1)
            yield StreamingChunk(
                chunk_id=f"chk_{i+1}",
                sequence=i + 1,
                delta_text=w + ("" if is_last else " "),
                is_final=is_last,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return provider statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "provider_type": self.provider_type.value,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "generations_count": self._generations_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report provider health status."""
        return ComponentHealth(
            component_name=f"LLMProvider_{self.provider_type.value}",
            status=SystemHealthStatus.HEALTHY,
            message=f"LLMProvider {self.provider_type.value} operational.",
        )
