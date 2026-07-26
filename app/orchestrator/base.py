"""Abstract orchestrator contracts and dependency protocols.

This module defines the replaceable boundaries for the AI orchestrator layer.
The orchestrator itself must not own business logic; it only coordinates
pluggable collaborators through these contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from app.schemas.chat import AIResponse, ChatRequest, ChatResponse
from app.schemas.context import ConversationContext, Intent, NavigationState
from app.schemas.planner import PlannerResponse
from app.schemas.memory import MemoryRecord
from app.schemas.tools import ToolCall, ToolResult


@runtime_checkable
class ConversationContextLoader(Protocol):
    """Load and persist conversation context for a request."""

    async def load(self, conversation_id: str, **kwargs: Any) -> ConversationContext | None:
        """Load the latest conversation context, if available."""

    async def save(self, context: ConversationContext, **kwargs: Any) -> None:
        """Persist the latest conversation context."""


@runtime_checkable
class PromptProvider(Protocol):
    """Resolve prompt variants without exposing storage details."""

    def get_system_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the active system prompt."""

    def get_navigation_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the navigation prompt."""

    def get_booking_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the booking prompt."""

    def get_pandit_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the pandit prompt."""


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic LLM execution contract."""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Generate a raw model response."""


@runtime_checkable
class StructuredOutputParser(Protocol):
    """Parse raw LLM output into typed orchestration artifacts."""

    def parse_ai_response(self, raw_output: str, **kwargs: Any) -> AIResponse:
        """Convert raw model output into a structured AI response."""

    def parse_chat_response(self, raw_output: str, **kwargs: Any) -> ChatResponse:
        """Convert raw model output into a chat response."""


@runtime_checkable
class RoutingPolicy(Protocol):
    """Decide which downstream subsystems must be invoked."""

    def requires_rag(self, intent: Intent | None, ai_response: AIResponse | None, **kwargs: Any) -> bool:
        """Return True when retrieval should be invoked."""

    def requires_tool_call(self, intent: Intent | None, ai_response: AIResponse | None, **kwargs: Any) -> bool:
        """Return True when tool execution should be invoked."""

    def requires_navigation(self, intent: Intent | None, navigation_state: NavigationState | None, **kwargs: Any) -> bool:
        """Return True when navigation handling is required."""

    def requires_planner(self, intent: Intent | None, ai_response: AIResponse | None, **kwargs: Any) -> bool:
        """Return True when planner coordination is required."""


@runtime_checkable
class RAGGateway(Protocol):
    """Boundary for retrieval-augmented generation coordination."""

    async def retrieve(self, request: ChatRequest, context: ConversationContext | None = None, **kwargs: Any) -> Any:
        """Retrieve supporting context for the current request."""


@runtime_checkable
class MemoryGateway(Protocol):
    """Boundary for durable memory coordination."""

    async def load(self, context: ConversationContext | None = None, **kwargs: Any) -> list[MemoryRecord]:
        """Load memory records relevant to the current request."""

    async def save(self, records: list[MemoryRecord], **kwargs: Any) -> None:
        """Persist memory records produced during orchestration."""


@runtime_checkable
class PlannerGateway(Protocol):
    """Boundary for planner coordination."""

    async def build_plan(self, request: ChatRequest, context: ConversationContext | None = None, **kwargs: Any) -> PlannerResponse:
        """Build a plan for the current request."""


@runtime_checkable
class ToolRegistry(Protocol):
    """Boundary for discovering available tools without hardcoding them."""

    def list_tool_names(self, **kwargs: Any) -> list[str]:
        """Return the names of available tools."""

    def has_tool(self, tool_name: str, **kwargs: Any) -> bool:
        """Return True when a tool is registered."""


@runtime_checkable
class NavigationGateway(Protocol):
    """Boundary for navigation coordination."""

    async def resolve(self, request: ChatRequest, context: ConversationContext | None = None, **kwargs: Any) -> NavigationState:
        """Resolve the next navigation state."""


@runtime_checkable
class ToolGateway(Protocol):
    """Boundary for tool lookup and execution coordination."""

    async def execute(self, tool_call: ToolCall, **kwargs: Any) -> ToolResult:
        """Execute a structured tool call and return the result."""


class BaseOrchestrator(ABC):
    """Abstract orchestration boundary for the AI brain.

    Concrete implementations should only coordinate dependencies. Business logic,
    policy, and domain behavior must live in injected collaborators.
    """

    @abstractmethod
    async def orchestrate(self, request: ChatRequest, **kwargs: Any) -> ChatResponse:
        """Execute the orchestration flow for a chat request."""
        raise NotImplementedError
