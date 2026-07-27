"""OpenRouter LLM provider implementation.

Communicates with OpenRouter Chat Completion API. Completely isolated provider implementation.
"""

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any

import httpx

from app.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InternalServerError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from app.llm.base import BaseLLMProvider
from app.llm.models import HealthStatus, LLMRequest, LLMResponse, TokenUsage
from app.llm.settings import LLMSettings, llm_settings

logger = logging.getLogger(__name__)

# Constants
PROVIDER_NAME: str = "openrouter"
CHAT_COMPLETIONS_ENDPOINT: str = "/chat/completions"
MODELS_ENDPOINT: str = "/models"
SSE_DATA_PREFIX: str = "data: "
SSE_DONE_MARKER: str = "[DONE]"
DEFAULT_USER_ROLE: str = "user"
DEFAULT_SYSTEM_ROLE: str = "system"
DEFAULT_USER_AGENT: str = "MantraSetu-AI/1.0"
MS_PER_SECOND: float = 1000.0
HTTP_OK_STATUS: int = 200
BACKOFF_EXPONENT_BASE: float = 2.0
RETRYABLE_STATUS_CODES: set[int] = {408, 429, 500, 502, 503, 504}


def _raise_for_http_status(exc: httpx.HTTPStatusError) -> None:
    """Raise appropriate application domain exception for non-retryable HTTP status codes."""
    status_code = exc.response.status_code
    response_text = exc.response.text
    details = {"status_code": status_code, "response": response_text}

    if status_code == 400:
        raise ValidationError(
            message=f"OpenRouter bad request (400): {response_text}",
            details=details,
        ) from exc
    elif status_code == 401:
        raise ExternalServiceError(
            message=f"OpenRouter unauthorized (401): {response_text}",
            details=details,
        ) from exc
    elif status_code == 403:
        raise ExternalServiceError(
            message=f"OpenRouter forbidden (403): {response_text}",
            details=details,
        ) from exc
    elif status_code == 404:
        raise ExternalServiceError(
            message=f"OpenRouter resource or model not found (404): {response_text}",
            details=details,
        ) from exc
    elif status_code == 409:
        raise ExternalServiceError(
            message=f"OpenRouter conflict (409): {response_text}",
            details=details,
        ) from exc
    elif status_code == 422:
        raise ValidationError(
            message=f"OpenRouter validation error (422): {response_text}",
            details=details,
        ) from exc
    else:
        raise InternalServerError(
            message=f"OpenRouter non-retryable HTTP error ({status_code}): {response_text}",
            error_code="PROVIDER_HTTP_ERROR",
            details=details,
        ) from exc


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API LLM provider implementation.

    Attributes:
        _settings (LLMSettings): Provider configuration settings instance.
        _client (httpx.AsyncClient): Reusable async HTTP client instance.
    """

    def __init__(
        self,
        settings: LLMSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize OpenRouterProvider using llm_settings or custom overrides.

        Args:
            settings: Optional custom LLMSettings override.
            client: Optional custom httpx.AsyncClient override.
        """
        self._settings = settings or llm_settings

        headers = self._build_headers()

        timeout = httpx.Timeout(
            connect=self._settings.timeout_connect,
            read=self._settings.timeout_read,
            write=self._settings.timeout_write,
            pool=self._settings.timeout_pool,
        )

        self._client = client or httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
        )

        logger.info(
            "OpenRouter provider initialized [provider=%s, model=%s]",
            self.provider_name,
            self.model_name,
        )

    # Provider Properties
    @property
    def provider_name(self) -> str:
        """Return provider name string."""
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        """Return configured model name string."""
        return self._settings.model

    @property
    def supported_models(self) -> Sequence[str]:
        """Return sequence of supported models."""
        return (self._settings.model,)

    @property
    def supports_streaming(self) -> bool:
        """Return True indicating streaming support."""
        return True

    @property
    def supports_tools(self) -> bool:
        """Return True indicating tool support."""
        return True

    @property
    def supports_vision(self) -> bool:
        """Return True indicating vision support."""
        return True

    # Private Helpers
    def _build_headers(self) -> dict[str, str]:
        """Construct default HTTP headers using LLMSettings.

        Returns:
            dict[str, str]: Request headers dictionary.
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "HTTP-Referer": self._settings.app_url,
            "X-Title": self._settings.app_name,
        }
        api_key_val = (
            self._settings.api_key.get_secret_value()
            if hasattr(self._settings.api_key, "get_secret_value")
            else str(self._settings.api_key)
        )
        if api_key_val:
            headers["Authorization"] = f"Bearer {api_key_val}"
        return headers

    def _validate_request(self, request: LLMRequest) -> None:
        """Validate incoming LLMRequest.

        Args:
            request: LLMRequest to validate.

        Raises:
            ValidationError: If request is invalid, or both prompt and messages are empty.
        """
        if request is None:
            raise ValidationError("LLMRequest cannot be None.")

        has_prompt = bool(request.prompt and request.prompt.strip())
        has_messages = bool(request.messages and isinstance(request.messages, list))

        if not has_prompt and not has_messages:
            raise ValidationError(
                "LLMRequest must contain either a non-empty prompt or a messages list."
            )

    def _build_payload(
        self,
        request: LLMRequest,
        stream: bool = False,
    ) -> dict[str, Any]:
        """Convert LLMRequest into OpenRouter payload JSON format.

        Args:
            request: Standardized request model.
            stream: Flag indicating whether streaming is enabled.

        Returns:
            dict[str, Any]: OpenRouter payload dictionary.
        """
        messages: list[dict[str, Any]] = []

        if request.messages:
            serialized_messages: list[dict[str, Any]] = []
            for msg in request.messages:
                if isinstance(msg, dict):
                    serialized_messages.append(msg)
                elif hasattr(msg, "role") and hasattr(msg, "content"):
                    serialized_messages.append(
                        {
                            "role": getattr(msg, "role"),
                            "content": getattr(msg, "content"),
                        }
                    )
                elif hasattr(msg, "model_dump"):
                    serialized_messages.append(msg.model_dump())
                else:
                    raise ValueError(f"Unsupported message type in LLMRequest.messages: {type(msg).__name__}")
            messages = serialized_messages
        else:
            if request.system_prompt and request.system_prompt.strip():
                messages.append(
                    {
                        "role": DEFAULT_SYSTEM_ROLE,
                        "content": request.system_prompt.strip(),
                    }
                )
            if request.prompt and request.prompt.strip():
                messages.append(
                    {
                        "role": DEFAULT_USER_ROLE,
                        "content": request.prompt.strip(),
                    }
                )

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": request.temperature,
            "stream": stream,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.stop is not None:
            payload["stop"] = request.stop

        if request.metadata:
            payload["metadata"] = request.metadata

        return payload

    def _extract_usage(self, response_data: dict[str, Any]) -> TokenUsage:
        """Extract token usage metrics from API response.

        Args:
            response_data: OpenRouter response payload.

        Returns:
            TokenUsage: Token consumption data.
        """
        usage_data = response_data.get("usage")
        if not isinstance(usage_data, dict):
            return TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        return TokenUsage(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
            completion_tokens=int(usage_data.get("completion_tokens", 0)),
            total_tokens=int(usage_data.get("total_tokens", 0)),
        )

    def _parse_response(self, response_data: dict[str, Any]) -> LLMResponse:
        """Parse raw OpenRouter JSON into a standardized LLMResponse object.

        Args:
            response_data: Parsed response JSON dictionary.

        Returns:
            LLMResponse: Standardized response model.

        Raises:
            InternalServerError: On malformed response.
        """
        if not isinstance(response_data, dict):
            raise InternalServerError(
                message="OpenRouter response payload must be a JSON dictionary.",
                error_code="INVALID_PROVIDER_RESPONSE",
            )

        choices = response_data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise InternalServerError(
                message="OpenRouter response contains no choice items.",
                error_code="INVALID_PROVIDER_RESPONSE",
            )

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise InternalServerError(
                message="OpenRouter choice object is invalid.",
                error_code="INVALID_PROVIDER_RESPONSE",
            )

        message_obj = first_choice.get("message", {})
        content = message_obj.get("content", "") if isinstance(message_obj, dict) else ""
        finish_reason = first_choice.get("finish_reason")
        model_used = response_data.get("model", self.model_name)
        usage = self._extract_usage(response_data)

        return LLMResponse(
            content=str(content),
            provider=self.provider_name,
            model=str(model_used),
            usage=usage,
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )

    async def _request(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute POST request against OpenRouter API with exponential retries.

        Args:
            url: Full target URL.
            payload: Request body JSON payload.

        Returns:
            dict[str, Any]: Parsed JSON response.

        Raises:
            InternalServerError: If all retries fail.
        """
        max_attempts = max(1, self._settings.max_retries + 1)
        backoff = self._settings.retry_backoff_seconds
        start_time = time.perf_counter()

        logger.info(
            "Sending OpenRouter API request [endpoint=%s, max_attempts=%d]",
            url,
            max_attempts,
        )

        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.post(url, json=payload)
                response.raise_for_status()

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.info(
                    "OpenRouter API response success [attempt=%d/%d, latency=%.2fms]",
                    attempt,
                    max_attempts,
                    duration_ms,
                )

                return response.json()

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES:
                    logger.error(
                        "Non-retryable OpenRouter HTTP error %d: %s",
                        status_code,
                        str(exc),
                    )
                    _raise_for_http_status(exc)

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "Retryable OpenRouter HTTP error %d [attempt=%d/%d, latency=%.2fms]: %s",
                    status_code,
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )
            except httpx.TimeoutException as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "OpenRouter request timeout [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )
            except (httpx.TransportError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "OpenRouter transport or decode error [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )

            if attempt < max_attempts:
                sleep_seconds = backoff * (BACKOFF_EXPONENT_BASE ** (attempt - 1))
                logger.info(
                    "Retrying OpenRouter request [attempt %d -> %d] in %.2f seconds",
                    attempt,
                    attempt + 1,
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)

        duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
        logger.error(
            "OpenRouter request failed after %d attempts [total_latency=%.2fms]: %s",
            max_attempts,
            duration_ms,
            str(last_error),
        )
        raise InternalServerError(
            message=f"OpenRouter request failed after {max_attempts} attempts: {last_error}",
            error_code="PROVIDER_REQUEST_FAILED",
        ) from last_error

    # Public Methods
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete text response asynchronously for an LLMRequest.

        Args:
            request: Standardized input request model.

        Returns:
            LLMResponse: Standardized response model with provider populated.

        Raises:
            ValueError: On request validation failure.
            InternalServerError: On API failure.
        """
        self._validate_request(request)

        url = f"{self._settings.base_url.rstrip('/')}{CHAT_COMPLETIONS_ENDPOINT}"
        payload = self._build_payload(request, stream=False)

        response_data = await self._request(url, payload)
        return self._parse_response(response_data)

    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream generated text chunks asynchronously using SSE.

        Args:
            request: Standardized input request model.

        Yields:
            str: Incremental text chunk from the model.

        Raises:
            ValueError: On request validation failure.
            InternalServerError: On streaming failure.
        """
        self._validate_request(request)

        url = f"{self._settings.base_url.rstrip('/')}{CHAT_COMPLETIONS_ENDPOINT}"
        payload = self._build_payload(request, stream=True)

        logger.info("OpenRouter stream started [model=%s]", self.model_name)

        try:
            async with self._client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    cleaned_line = line.strip()
                    if not cleaned_line or cleaned_line.startswith(":"):
                        continue

                    if not cleaned_line.startswith(SSE_DATA_PREFIX):
                        continue

                    data_str = cleaned_line[len(SSE_DATA_PREFIX):].strip()
                    if not data_str:
                        continue

                    if data_str == SSE_DONE_MARKER:
                        logger.info("OpenRouter stream finished [DONE received]")
                        break

                    try:
                        chunk_json = json.loads(data_str)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        logger.warning("Malformed SSE chunk skipped: %s", data_str[:50])
                        continue

                    if not isinstance(chunk_json, dict):
                        continue

                    choices = chunk_json.get("choices")
                    if not isinstance(choices, list) or not choices:
                        continue

                    first_choice = choices[0]
                    if not isinstance(first_choice, dict):
                        continue

                    delta = first_choice.get("delta")
                    if not isinstance(delta, dict):
                        continue

                    content_chunk = delta.get("content")
                    if content_chunk and isinstance(content_chunk, str):
                        yield content_chunk

        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as exc:
            logger.error("OpenRouter stream failed: %s", str(exc))
            raise InternalServerError(
                message=f"OpenRouter streaming failed: {exc}",
                error_code="PROVIDER_STREAMING_FAILED",
            ) from exc

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Alias method for stream_generate.

        Args:
            request: Standardized input request model.

        Yields:
            str: Incremental text chunk from the model.
        """
        async for chunk in self.stream_generate(request):
            yield chunk

    async def health_check(self) -> HealthStatus:
        """Perform a lightweight health check request against OpenRouter.

        Returns:
            HealthStatus: Standardized health status model.
        """
        url = f"{self._settings.base_url.rstrip('/')}{MODELS_ENDPOINT}"
        start_time = time.perf_counter()

        try:
            response = await self._client.get(url)
            latency_ms = (time.perf_counter() - start_time) * MS_PER_SECOND

            if response.status_code == HTTP_OK_STATUS:
                logger.info("OpenRouter health check passed [latency=%.2fms]", latency_ms)
                return HealthStatus(
                    healthy=True,
                    provider=self.provider_name,
                    model=self.model_name,
                    latency_ms=latency_ms,
                    message="OpenRouter API is operational.",
                )

            logger.warning(
                "OpenRouter health check returned status %d [latency=%.2fms]",
                response.status_code,
                latency_ms,
            )
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=latency_ms,
                message=f"HTTP status {response.status_code}",
            )

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
            logger.error("OpenRouter health check failed: %s", str(exc))
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=latency_ms,
                message=f"Health check failed: {exc}",
            )

    async def close(self) -> None:
        """Close the underlying HTTP client gracefully."""
        await self._client.aclose()
