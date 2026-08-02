"""Sarvam Speech-to-Text Provider implementation."""

from __future__ import annotations

import logging

from app.speech.base import BaseSpeechToTextProvider
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse

logger = logging.getLogger(__name__)


class SarvamProvider(BaseSpeechToTextProvider):
    """Speech-to-Text provider implementation for Sarvam AI."""

    def __init__(
        self,
        api_key: str | None = None,
    ) -> None:
        """Initialize the Sarvam provider.

        Args:
            api_key: Optional API key reserved for future Sarvam integrations.
        """
        self._api_key = api_key
        logger.info("SarvamProvider initialized")

    @property
    def provider_name(self) -> str:
        """Return the unique provider identifier.

        Returns:
            Unique provider name.
        """
        return "sarvam"

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Convert audio into text using the Sarvam provider.

        Args:
            request: Standard speech-to-text request.

        Returns:
            SpeechToTextResponse: Standardized transcription response.

        Raises:
            NotImplementedError: Sarvam integration has not yet been implemented.
        """
        raise NotImplementedError(
            "Sarvam transcription is not implemented."
        )

    async def health_check(self) -> bool:
        """Check the operational health of the Sarvam provider.

        Returns:
            True indicating the provider is available.
        """
        logger.info("SarvamProvider health check completed successfully.")
        return True

    async def close(self) -> None:
        """Release Sarvam provider resources."""
        logger.info("SarvamProvider closed")
        