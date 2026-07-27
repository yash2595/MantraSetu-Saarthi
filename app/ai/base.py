"""Abstract contracts and interfaces for the AI subsystem in MantraSetu AgentOS.

This module defines abstract base classes for AI providers, embedding generators, speech synthesis/recognition,
vision analysis, and tool execution alongside domain exception hierarchies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator
from uuid import UUID

from app.ai.models import (
    AIRequest,
    AIResponse,
)


class AIError(Exception):
    """Base exception for all AI subsystem errors."""

    pass


class AIInitializationError(AIError):
    """Raised when an AI provider or service initialization fails."""

    pass


class AIProviderError(AIError):
    """Raised when an underlying AI provider returns an unrecoverable error."""

    pass


class AIRequestError(AIError):
    """Raised when an AI request payload or parameter configuration is invalid."""

    pass


class AIResponseError(AIError):
    """Raised when parsing or processing an AI response payload fails."""

    pass


class AIStreamingError(AIError):
    """Raised when a streaming response generator encounters an error."""

    pass


class AIHealthCheckError(AIError):
    """Raised when a diagnostic health check probe fails."""

    pass


class AIToolError(AIError):
    """Raised when tool execution or tool argument parsing fails."""

    pass


class BaseAIProvider(ABC):
    """Abstract interface defining the contract for AI inference provider backends."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider driver dependencies and API client state."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close provider resources and release active connections."""
        ...

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute a complete text/chat completion inference request.

        Args:
            request: Provider-independent AIRequest payload model.

        Returns:
            AIResponse: Provider-independent AIResponse output model.
        """
        ...

    @abstractmethod
    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Execute a streaming text/chat completion inference request.

        Args:
            request: Provider-independent AIRequest payload model.

        Yields:
            str | dict[str, object]: Incremental text or delta chunk data.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, object]:
        """Perform an operational health check and latency probe on the provider.

        Returns:
            dict[str, object]: Operational status dictionary.
        """
        ...


class BaseEmbeddingProvider(ABC):
    """Abstract interface defining the contract for text vector embedding generation."""

    @abstractmethod
    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Generate numerical vector embeddings for an input tuple of text strings.

        Args:
            texts: Immutable tuple of text strings to embed.

        Returns:
            tuple[tuple[float, ...], ...]: Tuple of floating-point embedding vectors.
        """
        ...


class BaseSpeechProvider(ABC):
    """Abstract interface defining contracts for Speech-to-Text (STT) and Text-to-Speech (TTS)."""

    @abstractmethod
    async def speech_to_text(
        self,
        audio_data: bytes,
        mime_type: str = "audio/wav",
    ) -> str:
        """Transcribe raw audio data bytes into a text transcript string.

        Args:
            audio_data: Raw audio binary data.
            mime_type: MIME audio format identifier (e.g. 'audio/wav', 'audio/mp3').

        Returns:
            str: Transcribed text string.
        """
        ...

    @abstractmethod
    async def text_to_speech(
        self,
        text: str,
        voice: str | None = None,
    ) -> bytes:
        """Synthesize input text string into raw speech audio binary data.

        Args:
            text: Input text string to synthesize.
            voice: Optional voice identifier string.

        Returns:
            bytes: Generated audio binary data bytes.
        """
        ...


class BaseVisionProvider(ABC):
    """Abstract interface defining contracts for image analysis and image generation."""

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> AIResponse:
        """Analyze an input image with a multimodal vision prompt.

        Args:
            image_bytes: Binary data bytes of the image file.
            prompt: Text prompt describing analysis query.

        Returns:
            AIResponse: Analysis output response model.
        """
        ...

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
    ) -> bytes:
        """Generate an image from a descriptive text prompt.

        Args:
            prompt: Text prompt describing desired image.
            width: Image width in pixels.
            height: Image height in pixels.

        Returns:
            bytes: Generated image binary file bytes.
        """
        ...


class BaseToolCallingProvider(ABC):
    """Abstract interface defining contracts for LLM tool capability probe and execution."""

    @abstractmethod
    async def supports_tools(self) -> bool:
        """Check if the provider capability includes function tool calling.

        Returns:
            bool: True if function tool calling is supported, False otherwise.
        """
        ...

    @abstractmethod
    async def execute_tools(
        self,
        tool_calls: tuple[object, ...],
    ) -> tuple[object, ...]:
        """Execute a tuple of requested tool calls.

        Args:
            tool_calls: Immutable tuple of tool call objects to execute.

        Returns:
            tuple[object, ...]: Immutable tuple of completed tool result objects.
        """
        ...
