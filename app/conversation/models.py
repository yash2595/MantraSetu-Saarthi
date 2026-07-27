"""Domain models and schemas for the Conversation subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models, message structures, turn representations,
context settings, and session models for framework-independent conversation management.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Metadata = dict[str, Any]


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseConversationModel(BaseModel):
    """Base Pydantic v2 model for immutable Conversation domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ConversationRole(str, Enum):
    """Enumeration of message roles in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class ConversationStatus(str, Enum):
    """Enumeration of conversation session operational statuses."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    ERROR = "error"


class ConversationMessage(BaseConversationModel):
    """Domain model representing a single conversation message.

    Attributes:
        message_id: Unique message identifier UUID.
        role: Role of the message sender (system, user, assistant, tool, function).
        content: Text content of the message.
        name: Optional author name or tool identifier.
        metadata: Arbitrary metadata key-value pairs.
        created_at: UTC timestamp when message was created.
    """

    message_id: UUID = Field(
        default_factory=uuid4,
        description="Unique message identifier UUID.",
    )
    role: ConversationRole = Field(
        ...,
        description="Role of the message sender.",
    )
    content: str = Field(
        ...,
        description="Text content of the message.",
    )
    name: str | None = Field(
        default=None,
        description="Optional author name or tool identifier.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC message creation timestamp.",
    )


class ConversationTurn(BaseConversationModel):
    """Domain model representing a single interaction turn (user prompt and assistant response).

    Attributes:
        turn_id: Unique turn identifier UUID.
        user_message: User message that initiated the turn.
        assistant_message: Optional assistant response message.
        system_messages: Tuple of system prompt messages active during turn.
        tool_messages: Tuple of tool call/result messages associated with turn.
        metadata: Arbitrary metadata key-value pairs.
        created_at: UTC creation timestamp.
    """

    turn_id: UUID = Field(
        default_factory=uuid4,
        description="Unique turn identifier UUID.",
    )
    user_message: ConversationMessage = Field(
        ...,
        description="User message initiating the turn.",
    )
    assistant_message: ConversationMessage | None = Field(
        default=None,
        description="Optional assistant response message.",
    )
    system_messages: tuple[ConversationMessage, ...] = Field(
        default_factory=tuple,
        description="Tuple of system messages active during turn.",
    )
    tool_messages: tuple[ConversationMessage, ...] = Field(
        default_factory=tuple,
        description="Tuple of tool messages executed during turn.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary turn metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC turn creation timestamp.",
    )


class ConversationContext(BaseConversationModel):
    """Domain model capturing configuration parameters and context variables for a session.

    Attributes:
        context_id: Unique context identifier UUID.
        system_prompt: System prompt string governing assistant behavior.
        variables: Key-value environment or context variables dictionary.
        max_tokens: Maximum token limit constraint.
        metadata: Arbitrary metadata key-value pairs.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    context_id: UUID = Field(
        default_factory=uuid4,
        description="Unique context identifier UUID.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="System prompt string governing assistant behavior.",
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value environment context variables dictionary.",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Optional maximum token limit constraint.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary context metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class ConversationSession(BaseConversationModel):
    """Domain model representing an entire conversation session history and state.

    Attributes:
        session_id: Unique conversation session identifier UUID.
        status: Operational status enum of the session.
        context: ConversationContext configuration for the session.
        turns: Immutable tuple of ConversationTurn instances in chronological order.
        metadata: Arbitrary session metadata key-value pairs.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique conversation session identifier UUID.",
    )
    status: ConversationStatus = Field(
        default=ConversationStatus.ACTIVE,
        description="Operational status enum of the session.",
    )
    context: ConversationContext = Field(
        default_factory=ConversationContext,
        description="ConversationContext configuration for the session.",
    )
    turns: tuple[ConversationTurn, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of ConversationTurn instances.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary session metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class ConversationBatch(BaseConversationModel):
    """Domain model representing a batch of conversation messages for bulk processing.

    Attributes:
        batch_id: Unique batch identifier UUID.
        session_id: Target conversation session identifier UUID.
        messages: Immutable tuple of ConversationMessage instances to process.
        created_at: UTC creation timestamp.
    """

    batch_id: UUID = Field(
        default_factory=uuid4,
        description="Unique batch identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Target conversation session identifier UUID.",
    )
    messages: tuple[ConversationMessage, ...] = Field(
        default_factory=tuple,
        description="Tuple of ConversationMessage instances.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC batch creation timestamp.",
    )
