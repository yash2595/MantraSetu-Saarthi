"""Qwen provider implementation."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.llm.base import BaseLLM
from app.llm.config import LLMSettings
from app.llm.exceptions import LLMConfigurationError, LLMRetryError, LLMTimeoutError

logger = logging.getLogger(__name__)


class QwenLLM(BaseLLM):
    """Lightweight async Qwen provider adapter.

    The class keeps the provider boundary narrow: the public API is only
    ``generate()``, while retries, timeout handling, and payload assembly stay
    internal.
    """

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings
        if not settings.qwen_api_key:
            raise LLMConfigurationError("LLM_QWEN_API_KEY is required for the Qwen provider")

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a response by calling the Qwen-compatible chat endpoint."""
        payload = self._build_payload(prompt, **kwargs)
        last_error: Exception | None = None

        for attempt in range(self._settings.max_retries + 1):
            try:
                logger.info(
                    "llm_request_start",
                    extra={
                        "provider": "qwen",
                        "attempt": attempt + 1,
                        "model": self._settings.qwen_model,
                    },
                )
                async with httpx.AsyncClient(
                    base_url=self._settings.qwen_base_url,
                    timeout=self._settings.timeout_seconds,
                    headers={"Authorization": f"Bearer {self._settings.qwen_api_key}"},
                ) as client:
                    response = await client.post("/chat/completions", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(
                        "llm_request_success",
                        extra={
                            "provider": "qwen",
                            "attempt": attempt + 1,
                            "model": self._settings.qwen_model,
                        },
                    )
                    return content
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "llm_request_timeout",
                    extra={
                        "provider": "qwen",
                        "attempt": attempt + 1,
                        "timeout_seconds": self._settings.timeout_seconds,
                    },
                )
            except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
                last_error = exc
                logger.exception(
                    "llm_request_failed",
                    extra={
                        "provider": "qwen",
                        "attempt": attempt + 1,
                        "model": self._settings.qwen_model,
                    },
                )

            if attempt < self._settings.max_retries:
                await asyncio.sleep(self._settings.retry_backoff_seconds * (attempt + 1))

        if isinstance(last_error, httpx.TimeoutException):
            raise LLMTimeoutError("Qwen request timed out") from last_error
        raise LLMRetryError("Qwen request failed after all retries") from last_error

    def _build_payload(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """Build a minimal chat-completions payload."""
        messages = kwargs.get(
            "messages",
            [
                {"role": "user", "content": prompt},
            ],
        )
        return {
            "model": self._settings.qwen_model,
            "messages": messages,
        }
