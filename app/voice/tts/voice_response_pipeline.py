"""VoiceResponsePipeline streaming coordinator converting InteractionResponse into audio streams."""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from uuid import uuid4

from app.schemas.api.interaction import InteractionResponse
from app.voice.schemas import AudioEncoding
from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import AudioChunk, VoiceSynthesisRequest

logger = logging.getLogger(__name__)


class VoiceResponsePipeline:
    """Stream coordinator converting normalized InteractionResponse into streamed AudioChunk frames."""

    def __init__(self, tts_provider: ITTSProvider) -> None:
        if tts_provider is None:
            raise ValueError("VoiceResponsePipeline requires a non-null ITTSProvider instance.")
        self._tts_provider = tts_provider

    @property
    def tts_provider(self) -> ITTSProvider:
        """Expose injected ITTSProvider implementation."""
        return self._tts_provider

    async def process_response(
        self,
        response: InteractionResponse,
        voice: str | None = None,
        language: str | None = None,
        encoding: AudioEncoding = AudioEncoding.MP3,
    ) -> AsyncGenerator[AudioChunk, None]:
        """Convert InteractionResponse content into streaming AudioChunk sequence.

        Args:
            response: Normalized InteractionResponse from Module 1 AIOrchestrator.
            voice: Optional target voice override. Defaults to response metadata or 'meera'.
            language: Optional target language override. Defaults to response metadata or 'hi'.
            encoding: AudioEncoding format enum.

        Yields:
            AudioChunk: Streamed audio frames with correlation metadata.
        """
        text_content = response.content.strip() if response.content else "Namaste"

        resolved_voice = voice or response.metadata.get("voice") or "meera"
        resolved_language = language or response.metadata.get("language") or "hi"

        synthesis_request = VoiceSynthesisRequest(
            request_id=response.request_id or uuid4(),
            session_id=response.session_id,
            conversation_id=response.conversation_id,
            text=text_content,
            language=resolved_language,
            voice=resolved_voice,
            encoding=encoding,
            metadata=dict(response.metadata),
        )

        logger.info(
            "VoiceResponsePipeline processing InteractionResponse for TTS",
            extra={
                "request_id": str(synthesis_request.request_id),
                "session_id": response.session_id,
                "conversation_id": str(response.conversation_id) if response.conversation_id else None,
                "text_length": len(text_content),
                "provider": self._tts_provider.provider_name,
                "voice": resolved_voice,
                "language": resolved_language,
            },
        )

        async for chunk in self._tts_provider.stream(synthesis_request):
            yield chunk

    async def cancel(self, request_id: str) -> None:
        """Cancel an active TTS synthesis stream."""
        await self._tts_provider.cancel(request_id)
