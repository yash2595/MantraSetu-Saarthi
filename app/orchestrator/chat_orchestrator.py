"""Chat orchestration for the MantraSetu backend.

This coordinator only wires dependencies together. It does not contain any
business rules, routing heuristics, or provider-specific logic.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.llm.exceptions import LLMConfigurationError, LLMError
from app.orchestrator.context import OrchestratorContext, OrchestratorDependencies, OrchestratorState
from app.orchestrator.pipeline import DEFAULT_PIPELINE, OrchestrationPipeline
from app.schemas.chat import AIResponse, ChatRequest
from app.schemas.context import ConversationContext

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Dependency-injected coordinator for a single chat request."""

    def __init__(
        self,
        dependencies: OrchestratorDependencies,
        pipeline: OrchestrationPipeline | None = None,
    ) -> None:
        self._dependencies = dependencies
        self._pipeline = pipeline or DEFAULT_PIPELINE

    @property
    def pipeline(self) -> OrchestrationPipeline:
        """Expose the orchestration pipeline for debugging and testing."""
        return self._pipeline

    async def handle(self, request: ChatRequest) -> AIResponse:
        """Coordinate the request through context, prompt, and LLM layers."""
        context = await self._load_context(request)
        orchestrator_context = OrchestratorContext(
            dependencies=self._dependencies,
            state=OrchestratorState(request=request, conversation_context=context),
        )

        resolved_prompt_name = self._resolve_prompt_name(request, context)
        resolved_prompt = self._resolve_prompt(request, context, resolved_prompt_name)
        orchestrator_context.state.resolved_prompt = resolved_prompt

        prepared_request = self._prepare_request(request, resolved_prompt_name, resolved_prompt, context)
        try:
            ai_response = await self._dependencies.llm_client.generate(prepared_request)
        except LLMConfigurationError as exc:
            logger.warning(
                "llm_provider_not_configured",
                extra={
                    "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                    "prompt_name": resolved_prompt_name,
                    "pipeline": self._pipeline.name,
                },
            )
            return AIResponse(
                content="MantraSetu AI is configured but no LLM provider is connected yet.",
                provider=None,
                model=None,
                finish_reason="provider_not_configured",
                metadata={
                    "intent": "general_chat",
                    "confidence": 0.0,
                    "prompt_name": resolved_prompt_name,
                    "pipeline": self._pipeline.name,
                },
            )
        except LLMError as exc:
            logger.exception(
                "llm_provider_failed",
                extra={
                    "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                    "prompt_name": resolved_prompt_name,
                    "pipeline": self._pipeline.name,
                },
            )
            return AIResponse(
                content="MantraSetu AI could not process this request right now.",
                provider=None,
                model=None,
                finish_reason="provider_error",
                metadata={
                    "intent": "general_chat",
                    "confidence": 0.0,
                    "error": exc.__class__.__name__,
                    "prompt_name": resolved_prompt_name,
                    "pipeline": self._pipeline.name,
                },
            )

        orchestrator_context.state.ai_response = ai_response
        logger.info(
            "chat_orchestration_completed",
            extra={
                "conversation_id": str(request.conversation_id) if request.conversation_id else None,
                "prompt_name": resolved_prompt_name,
                "pipeline": self._pipeline.name,
            },
        )
        return ai_response

    async def _load_context(self, request: ChatRequest) -> ConversationContext | None:
        """Load conversation state when a context loader is available."""
        loader = self._dependencies.context_loader
        if request.conversation_id is None:
            return request.context

        if loader is None:
            return request.context

        loaded = await loader.load(str(request.conversation_id), request=request)
        return loaded or request.context

    def _resolve_prompt_name(self, request: ChatRequest, context: ConversationContext | None) -> str:
        """Choose a prompt name from request metadata or the active context."""
        metadata = request.metadata or {}
        prompt_name = metadata.get("prompt_name")
        if isinstance(prompt_name, str) and prompt_name.strip():
            return prompt_name.strip().lower()

        if context is not None and context.intent is not None:
            return context.intent.name.strip().lower()

        return "system"

    def _resolve_prompt(self, request: ChatRequest, context: ConversationContext | None, prompt_name: str) -> str:
        """Resolve the prompt text through the injected prompt provider."""
        prompt_provider = self._dependencies.prompt_provider
        prompt_version = (request.metadata or {}).get("prompt_version")
        prompt_variables = self._build_prompt_variables(request, context)

        if prompt_name == "navigation":
            return prompt_provider.get_navigation_prompt(version=prompt_version, **prompt_variables)
        if prompt_name == "booking":
            return prompt_provider.get_booking_prompt(version=prompt_version, **prompt_variables)
        if prompt_name == "pandit":
            return prompt_provider.get_pandit_prompt(version=prompt_version, **prompt_variables)
        return prompt_provider.get_system_prompt(version=prompt_version, **prompt_variables)

    def _build_prompt_variables(self, request: ChatRequest, context: ConversationContext | None) -> dict[str, Any]:
        """Build prompt variables without embedding business rules."""
        variables: dict[str, Any] = {
            "message": request.message,
            "stream": request.stream,
            "language": request.language or "",
        }
        if context is not None:
            variables["conversation_id"] = context.conversation_id
            variables["user_id"] = context.user_id or ""
            variables["locale"] = context.locale
            variables["timezone"] = context.timezone or ""
        return variables

    def _prepare_request(
        self,
        request: ChatRequest,
        prompt_name: str,
        resolved_prompt: str,
        context: ConversationContext | None,
    ) -> ChatRequest:
        """Return a request copy with orchestration metadata attached."""
        metadata = dict(request.metadata or {})
        metadata.update(
            {
                "prompt_name": prompt_name,
                "resolved_prompt": resolved_prompt,
                "pipeline": self._pipeline.name,
            }
        )
        if context is not None:
            metadata["loaded_context"] = context.model_dump(mode="json")

        return request.model_copy(update={"metadata": metadata, "context": context or request.context})
