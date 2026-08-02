"""Voice Gateway and Speech-to-Text Subsystem (Module 2)."""

from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import (
    InvalidAudioChunk,
    MicrophoneDisconnected,
    SpeechProviderUnavailable,
    SpeechRecognitionTimeout,
    UnsupportedAudioCodec,
    VoiceGatewayError,
    WebSocketDisconnected,
)
from app.voice.factory import build_voice_gateway, build_websocket_voice_handler
from app.voice.gateway import VoiceGateway
from app.voice.schemas import AudioConfig, WebSocketMessage, WebSocketMessageType
from app.voice.session import VoiceSession, VoiceSessionStatus
from app.voice.session_manager import VoiceSessionManager
from app.voice.transcript import TranscriptAggregator
from app.voice.websocket import WebSocketVoiceHandler

__all__ = [
    "AudioBuffer",
    "AudioConfig",
    "InvalidAudioChunk",
    "MicrophoneDisconnected",
    "SpeechProviderUnavailable",
    "SpeechRecognitionTimeout",
    "TranscriptAggregator",
    "UnsupportedAudioCodec",
    "VoiceGateway",
    "VoiceGatewayError",
    "VoiceSession",
    "VoiceSessionManager",
    "VoiceSessionStatus",
    "WebSocketDisconnected",
    "WebSocketMessage",
    "WebSocketMessageType",
    "WebSocketVoiceHandler",
    "build_voice_gateway",
    "build_websocket_voice_handler",
]
