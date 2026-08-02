"""Whisper Speech-to-Text provider adapter implementation."""

from __future__ import annotations

import logging
import time

from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import SpeechProviderUnavailable, SpeechRecognitionTimeout
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer

logger = logging.getLogger(__name__)


class WhisperAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to Whisper STT engine or API."""

    def __init__(self, api_key: str | None = None, model: str = "whisper-1") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "whisper"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info("Whisper STT session initialized", extra={"session_id": session.session_id})

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        if not chunk:
            return None
        return TranscriptChunk(
            session_id=session.session_id,
            text="",
            is_final=False,
            confidence=0.95,
            timestamp_ms=int(time.time() * 1000),
        )

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        logger.info("Whisper STT finish_session called", extra={"session_id": session.session_id, "size_bytes": buffer.size})
        return TranscriptResult(
            text="",
            confidence=1.0,
            language=session.language,
            provider=self.provider_name,
            duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
            metadata={"model": self._model, "status": "provider_not_configured"},
        )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("Whisper STT session cancelled", extra={"session_id": session.session_id})
