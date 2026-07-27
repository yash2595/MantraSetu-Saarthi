"""Abstract Base Provider interface for Text-to-Speech services.

Defines the contract that all TTS provider adapters (e.g. FishSpeech, CosyVoice)
must implement.
"""

from abc import ABC, abstractmethod

from app.tts.models import TextToSpeechRequest, TextToSpeechResponse


class BaseTextToSpeechProvider(ABC):
    """Abstract base class contract for all Text-to-Speech providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider unique string identifier.

        Returns:
            str: Unique string identifier of the provider.
        """
        raise NotImplementedError

    @abstractmethod
    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Convert input text request into synthesized audio response.

        Args:
            request: Standardized TextToSpeechRequest model.

        Returns:
            TextToSpeechResponse: Synthesized audio response model.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health status of the TTS provider.

        Returns:
            bool: True if provider API is healthy and reachable, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release provider connections and underlying resources."""
        raise NotImplementedError
