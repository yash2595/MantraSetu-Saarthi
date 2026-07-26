"""
Default dependency composition for the MantraSetu AI Backend.

This module wires together all default implementations required by the
ChatOrchestrator. Every dependency can later be replaced by Memory,
RAG, Planner, Navigation, Tool Calling, etc.
"""

from __future__ import annotations

from typing import Any

from app.llm.providers.openrouter_provider import OpenRouterProvider
from app.orchestrator.chat_orchestrator import ChatOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.base import (
    ConversationContextLoader,
    RoutingPolicy,
    StructuredOutputParser,
)
from app.prompts.prompt_manager import PromptManager
from app.schemas.chat import AIResponse, ChatResponse
from app.schemas.context import (
    ConversationContext,
    Intent,
    NavigationState,
)


class NoopConversationContextLoader(ConversationContextLoader):
    """Temporary conversation loader."""

    async def load(
        self,
        conversation_id: str,
        **kwargs: Any,
    ) -> ConversationContext | None:
        return None

    async def save(
        self,
        context: ConversationContext,
        **kwargs: Any,
    ) -> None:
        return None


class PassThroughStructuredOutputParser(StructuredOutputParser):
    """Simple parser until structured outputs are introduced."""

    def parse_ai_response(
        self,
        raw_output: str,
        **kwargs: Any,
    ) -> AIResponse:

        return AIResponse(
            content=raw_output,
        )

    def parse_chat_response(
        self,
        raw_output: str,
        **kwargs: Any,
    ) -> ChatResponse:

        return ChatResponse(
            assistant_message=raw_output,
        )


class DefaultRoutingPolicy(RoutingPolicy):
    """Everything disabled until Planner/Navigation is implemented."""

    def requires_rag(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_tool_call(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_navigation(
        self,
        intent: Intent |None,
        navigation_state: NavigationState | None,
        **kwargs: Any,
    ) -> bool:
        return False

    def requires_planner(
        self,
        intent: Intent | None,
        ai_response: AIResponse | None,
        **kwargs: Any,
    ) -> bool:
        return False


def build_chat_orchestrator() -> ChatOrchestrator:
    """
    Build the default dependency graph.
    """

    dependencies = OrchestratorDependencies(

        context_loader=NoopConversationContextLoader(),

        prompt_provider=PromptManager(),

        llm_client=OpenRouterProvider(),

        output_parser=PassThroughStructuredOutputParser(),

        routing_policy=DefaultRoutingPolicy(),

        memory_gateway=None,

        rag_gateway=None,

        planner_gateway=None,

        navigation_gateway=None,

        tool_registry=None,

        tool_gateway=None,
    )

    return ChatOrchestrator(
        dependencies=dependencies,
    )