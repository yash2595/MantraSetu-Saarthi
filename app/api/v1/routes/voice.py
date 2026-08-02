"""Voice REST API router module for API v1.

Provides HTTP endpoints for speech-to-text transcription, voice pipeline chat,
text-to-speech synthesis, and voice system health status via ConversationService.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerException,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from app.dependencies.providers import get_conversation_service
from app.services.conversation_service import ConversationService
from app.speech.models import (
    SpeechToTextRequest,
    SpeechToTextResponse,
    VoiceChatRequest,
    VoiceChatResponse,
)
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse

router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)


def _raise_http_exception(exc: Exception) -> None:
    """Map application exceptions to appropriate HTTP responses."""

    if isinstance(exc, BadRequestError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if isinstance(exc, UnauthorizedError):
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if isinstance(exc, InternalServerException):
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    raise HTTPException(
        status_code=500,
        detail="Unexpected internal server error.",
    ) from exc


@router.post(
    "/transcribe",
    response_model=SpeechToTextResponse,
    summary="Transcribe audio payload to text",
)
async def transcribe_speech(
    request: SpeechToTextRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> SpeechToTextResponse:
    """Transcribe raw audio bytes into text."""
    try:
        return await conversation_service.speech_to_text(request)
    except Exception as exc:
        _raise_http_exception(exc)


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    summary="Execute end-to-end voice/text conversation pipeline",
)
async def generate_chat_response(
    request: VoiceChatRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> VoiceChatResponse:
    """Execute complete voice conversation pipeline."""
    try:
        return await conversation_service.process_voice_chat(request)
    except Exception as exc:
        _raise_http_exception(exc)


@router.post(
    "/synthesize",
    response_model=TextToSpeechResponse,
    summary="Synthesize text into speech",
)
async def synthesize_speech(
    request: TextToSpeechRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> TextToSpeechResponse:
    """Convert text into synthesized speech."""
    try:
        return await conversation_service.text_to_speech(request)
    except Exception as exc:
        _raise_http_exception(exc)


@router.get(
    "/health",
    summary="Check voice pipeline health status",
)
async def get_voice_health(
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    """Return health information for the voice pipeline."""
    try:
        return await conversation_service.health_check()
    except Exception as exc:
        _raise_http_exception(exc)