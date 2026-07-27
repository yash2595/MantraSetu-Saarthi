"""Qwen AI Provider implementation for MantraSetu AgentOS.

This module provides QwenAIProvider implementing BaseAIProvider for Qwen (DashScope) models
using OpenAI-compatible HTTP REST endpoints with strict dependency injection, explicit request/response mapping,
and comprehensive exception translation into domain models and ComponentHealth probes.
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from app.ai.base import (
    AIInitializationError,
    AIInferenceError,
    AIProviderError,
    AIRequestError,
    AIResponseError,
    BaseAIProvider,
)
from app.ai.models import (
    AIRequest,
    AIResponse,
    AIStatus,
    TokenUsage,
)
from app.core.models import ComponentHealth, SystemHealthStatus


class QwenAIProvider(BaseAIProvider):
    """Production-grade Qwen AI Provider implementing BaseAIProvider contract.

    Responsibility:
        Translates provider-independent AIRequest models into Qwen OpenAI-compatible REST API payloads,
        manages asynchronous HTTP connection lifecycles via httpx.AsyncClient, translates provider JSON responses
        into immutable domain models, streams token chunks, and maps network errors into domain exceptions.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen-max",
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        timeout: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize QwenAIProvider with injected parameters.

        Args:
            api_key: DashScope API key string.
            model: Default Qwen model identifier string.
            base_url: Base URL for DashScope OpenAI-compatible API.
            timeout: Connection/read timeout in seconds.
            client: Optional injected httpx.AsyncClient for dependency injection.
        """
        self._api_key = api_key
        self._default_model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = client
        self._client_owned = client is None
        self._initialized = False

    @property
    def provider_name(self) -> str:
        """Return unique provider identifier name string.

        Returns:
            str: Provider identifier name string.
        """
        return "qwen"

    def _get_client(self) -> httpx.AsyncClient:
        """Retrieve verified active AsyncClient instance.

        Returns:
            httpx.AsyncClient: Verified client instance.

        Raises:
            AIInitializationError: If provider or client is not initialized.
        """
        if not self._initialized or self._client is None:
            raise AIInitializationError(
                "QwenAIProvider is not initialized. Call initialize() first."
            )
        return self._client

    async def initialize(self) -> None:
        """Initialize HTTP client and connection pool.

        Raises:
            AIInitializationError: If httpx is missing or API key is empty.
        """
        if self._initialized:
            return

        if httpx is None:
            raise AIInitializationError(
                "The 'httpx' package is required for QwenAIProvider but is not installed."
            )

        if not self._api_key:
            raise AIInitializationError("QwenAIProvider requires a non-empty api_key.")

        if self._client_owned:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )

        self._initialized = True

    async def close(self) -> None:
        """Close internally managed HTTP client connections."""
        if self._client and self._client_owned:
            await self._client.aclose()
            self._client = None
        self._initialized = False

    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute a complete text/chat completion inference request against Qwen API.

        Args:
            request: Provider-independent AIRequest model.

        Returns:
            AIResponse: Domain AIResponse model.

        Raises:
            AIInitializationError: If provider is uninitialized.
            AIRequestError: If request payload validation fails.
            AIInferenceError: If remote HTTP connection, timeout, or status code fails.
            AIResponseError: If response payload parsing fails.
        """
        client = self._get_client()
        start_time = time.perf_counter()
        payload = self._build_request_payload(request, stream=False)
        target_model = request.model or self._default_model

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as e:
            raise AIInferenceError(f"Qwen API request timed out after {self._timeout}s.") from e
        except httpx.HTTPStatusError as e:
            err_text = e.response.text if e.response is not None else str(e)
            raise AIInferenceError(
                f"Qwen HTTP status error {e.response.status_code}: {err_text}"
            ) from e
        except httpx.RequestError as e:
            raise AIInferenceError(f"Qwen HTTP connection failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise AIResponseError(f"Invalid JSON received from Qwen API: {str(e)}") from e
        except Exception as e:
            raise AIInferenceError(f"Unexpected Qwen provider failure: {str(e)}") from e

        latency_ms = (time.perf_counter() - start_time) * 1000
        return self._parse_response(data, request.request_id, target_model, latency_ms)

    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Execute a streaming chat completion request yielding incremental chunk data.

        Args:
            request: Provider-independent AIRequest model.

        Yields:
            str | dict[str, object]: Incremental token or delta data.

        Raises:
            AIInitializationError: If provider is uninitialized.
            AIInferenceError: If streaming connection fails.
        """
        client = self._get_client()
        payload = self._build_request_payload(request, stream=True)

        try:
            async with client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    yield data_str
        except httpx.TimeoutException as e:
            raise AIInferenceError("Qwen streaming connection timed out.") from e
        except httpx.HTTPStatusError as e:
            err_text = e.response.text if e.response is not None else str(e)
            raise AIInferenceError(
                f"Qwen streaming HTTP error {e.response.status_code}: {err_text}"
            ) from e
        except httpx.RequestError as e:
            raise AIInferenceError(f"Qwen streaming connection failed: {str(e)}") from e
        except Exception as e:
            raise AIInferenceError(f"Unexpected Qwen streaming failure: {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Perform a lightweight health check probe using the models metadata endpoint.

        Returns:
            ComponentHealth: Operational component health model.
        """
        if not self._initialized or self._client is None:
            return ComponentHealth(
                component_name=self.provider_name,
                status=SystemHealthStatus.UNHEALTHY,
                message="QwenAIProvider is uninitialized.",
            )

        start_time = time.perf_counter()
        try:
            response = await self._client.get("/models")
            response.raise_for_status()
            latency = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                component_name=self.provider_name,
                status=SystemHealthStatus.HEALTHY,
                latency_ms=latency,
                message="Qwen models endpoint probe healthy.",
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                component_name=self.provider_name,
                status=SystemHealthStatus.UNHEALTHY,
                latency_ms=latency,
                message=f"Qwen health probe failed: {str(e)}",
            )

    # ------------------------------------------------------------------
    # Private Payload Builders & Parsers
    # ------------------------------------------------------------------

    def _build_request_payload(
        self,
        request: AIRequest,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Convert domain AIRequest model into OpenAI-compatible Qwen API payload.

        Args:
            request: Domain AIRequest model.
            stream: Boolean flag enabling SSE stream mode.

        Returns:
            dict[str, Any]: JSON serializable payload dictionary.
        """
        msg = request.message
        payload: dict[str, Any] = {
            "model": request.model or self._default_model,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                }
            ],
            "stream": stream,
        }
        return payload

    def _parse_response(
        self,
        data: dict[str, Any],
        request_id: Any,
        model: str,
        latency_ms: float,
    ) -> AIResponse:
        """Parse raw response JSON dictionary into domain AIResponse model.

        Args:
            data: API response dictionary.
            request_id: Associated request UUID.
            model: Model identifier string.
            latency_ms: Execution latency in milliseconds.

        Returns:
            AIResponse: Immutable domain model.

        Raises:
            AIResponseError: If required fields or choices are missing.
        """
        try:
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise AIResponseError("Qwen API response missing valid 'choices' array.")

            choice = choices[0]
            msg_data = choice.get("message", {})
            content = msg_data.get("content") or ""

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

            return AIResponse(
                request_id=request_id,
                content=content,
                model=model,
                status=AIStatus.SUCCESS,
                usage=usage,
                execution_time_ms=latency_ms,
            )
        except AIResponseError:
            raise
        except (KeyError, TypeError, ValueError) as e:
            raise AIResponseError(f"Failed to parse Qwen response payload: {str(e)}") from e
