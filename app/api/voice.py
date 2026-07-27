"""Voice REST API router module.

Provides HTTP endpoints for speech-to-text transcription, AI chat generation,
text-to-speech synthesis, and voice system health status via ConversationService.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies.providers import get_conversation_service
from app.llm.models import LLMRequest, LLMResponse
from app.services.conversation_service import ConversationService
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse
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
    response_model=LLMResponse,
    summary="Generate AI response completion",
)
async def generate_chat_response(
    request: LLMRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> LLMResponse:
    """Generate an AI text response completion from an LLM request.

    Args:
        request: LLMRequest model.
        conversation_service: Injected ConversationService dependency.

    Returns:
        LLMResponse: Standardized AI completion response model.

    Raises:
        HTTPException: On internal processing failure.
    """
    try:
        return await conversation_service.generate_response(request)
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
