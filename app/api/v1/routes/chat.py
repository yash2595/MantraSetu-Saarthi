"""Chat endpoint for the MantraSetu backend."""

from __future__ import annotations

import traceback

from fastapi import APIRouter, Depends, HTTPException

from app.llm.exceptions import LLMError
from app.orchestrator.chat_orchestrator import ChatOrchestrator
from app.orchestrator.defaults import build_chat_orchestrator
from app.schemas.chat import AIResponse, ChatRequest

router = APIRouter()


def get_chat_orchestrator() -> ChatOrchestrator:
    """Return the default chat orchestrator instance."""
    return build_chat_orchestrator()


@router.post("/chat", response_model=AIResponse)
async def chat_endpoint(
    request: ChatRequest,
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),
) -> AIResponse:
    try:
        return await orchestrator.handle(request)

    except LLMError as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc