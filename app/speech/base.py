"""Abstract Base Provider interface for Speech-to-Text services.

Defines the contract that all STT provider adapters (e.g. Sarvam, Whisper, Deepgram)
must implement.
"""

from abc import ABC, abstractmethod

from app.speech.models import SpeechToTextRequest, SpeechToTextResponse


class BaseSpeechToTextProvider(ABC):
    """Abstract base class contract for all Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Convert input audio payload into a standardized text response.

        Args:
            request: Standardized SpeechToTextRequest model.

        Returns:
            SpeechToTextResponse: Standardized transcript output response model.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Check the operational health status of the speech provider.

        Returns:
            bool: True if provider API is healthy and reachable, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release provider connections and underlying HTTP resources."""
        raise NotImplementedError
