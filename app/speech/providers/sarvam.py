"""Sarvam AI Speech-to-Text Provider implementation module."""

import logging

from app.speech.base import BaseSpeechToTextProvider
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse

logger = logging.getLogger(__name__)


class SarvamProvider(BaseSpeechToTextProvider):
    """Sarvam AI Speech-to-Text provider adapter implementation."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the SarvamProvider instance.

        Args:
            api_key: Optional API key string for authenticating with Sarvam AI API.
        """
        self._api_key = api_key
        logger.info("SarvamProvider initialized")

    @property
    def provider_name(self) -> str:
        """Return provider unique string identifier.

        Returns:
            str: Provider name string 'sarvam'.
        """
        return "sarvam"

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Transcribe an audio request using Sarvam AI API.

        Args:
            request: SpeechToTextRequest payload.

        Returns:
            SpeechToTextResponse: Transcribed output model.

        Raises:
            NotImplementedError: Always raised until external Sarvam SDK integration.
        """
        raise NotImplementedError("Sarvam transcription is not implemented.")

    async def health_check(self) -> bool:
        """Check operational health status of Sarvam AI provider.

        Returns:
            bool: Always returns True.
        """
        logger.info("SarvamProvider health check completed successfully")
        return True

    async def close(self) -> None:
        """Gracefully release Sarvam AI provider resources."""
        logger.info("SarvamProvider closed")
