"""Voice REST API router module for API v1.

Provides HTTP endpoints for speech-to-text transcription, voice pipeline chat,
text-to-speech synthesis, and voice system health status via ConversationService.
"""

from fastapi import APIRouter, Depends, HTTPException

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


@router.post(
    "/transcribe",
    response_model=SpeechToTextResponse,
    summary="Transcribe audio payload to text",
)
async def transcribe_speech(
    request: SpeechToTextRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> SpeechToTextResponse:
    """Transcribe raw audio bytes into a textual transcript.

    Args:
        request: SpeechToTextRequest model.
        conversation_service: Injected ConversationService dependency.

    Returns:
        SpeechToTextResponse: Transcribed textual output model.

    Raises:
        HTTPException: On internal processing failure.
    """
    try:
        return await conversation_service.speech_to_text(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/chat",
    response_model=VoiceChatResponse,
    summary="Execute end-to-end voice/text conversation pipeline",
)
async def generate_chat_response(
    request: VoiceChatRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> VoiceChatResponse:
    """Execute end-to-end voice conversation pipeline (STT -> LLM -> TTS).

    Args:
        request: VoiceChatRequest model containing prompt or audio_bytes.
        conversation_service: Injected ConversationService dependency.

    Returns:
        VoiceChatResponse: Standardized response with transcript, assistant_text, audio, and latencies.

    Raises:
        HTTPException: On internal processing failure.
    """
    try:
        return await conversation_service.process_voice_chat(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/synthesize",
    response_model=TextToSpeechResponse,
    summary="Synthesize text to audio speech",
)
async def synthesize_speech(
    request: TextToSpeechRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> TextToSpeechResponse:
    """Synthesize input text into raw audio binary payload.

    Args:
        request: TextToSpeechRequest model.
        conversation_service: Injected ConversationService dependency.

    Returns:
        TextToSpeechResponse: Synthesized audio response model.

    Raises:
        HTTPException: On internal processing failure.
    """
    try:
        return await conversation_service.text_to_speech(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get(
    "/health",
    response_model=dict[str, bool],
    summary="Check voice pipeline health status",
)
async def get_voice_health(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict[str, bool]:
    """Check the health status of all voice pipeline services.

    Args:
        conversation_service: Injected ConversationService dependency.

    Returns:
        dict[str, bool]: Dictionary indicating healthy status.

    Raises:
        HTTPException: On health check processing failure.
    """
    try:
        is_healthy = await conversation_service.health_check()
        return {"healthy": is_healthy}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
