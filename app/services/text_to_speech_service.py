"""Text-to-Speech Orchestration Service module.

Acts as an application service layer delegating speech synthesis operations
to an injected BaseTextToSpeechProvider adapter.
"""

from app.services.base import BaseService
from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse


class TextToSpeechService(BaseService):
    """Application service for orchestrating Text-to-Speech synthesis operations."""

    def __init__(self, provider: BaseTextToSpeechProvider) -> None:
        """Initialize TextToSpeechService with an injected TTS provider adapter.

        Args:
            provider: Injected BaseTextToSpeechProvider instance.
        """
        self._provider = provider

    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Synthesize text into speech using the underlying provider adapter.

        Args:
            request: Standardized TextToSpeechRequest model.

        Returns:
            TextToSpeechResponse: Standardized audio output response model.
        """
        return await self._provider.synthesize(request)

    async def health_check(self) -> bool:
        """Check operational health status of the underlying provider adapter.

        Returns:
            bool: True if provider is healthy, False otherwise.
        """
        return await self._provider.health_check()

    async def close(self) -> None:
        """Gracefully release underlying provider resources."""
        await self._provider.close()
