"""Session Management Pydantic Models.

Defines schemas for conversation messages, session state, context, and TTL tracking.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Helper to return current UTC timestamp."""
    return datetime.now(timezone.utc)


class SessionMessage(BaseModel):
    """Individual conversation message stored in session history.

    Attributes:
        message_id: Unique message identifier string.
        role: Message role string (e.g. 'user', 'assistant', 'system').
        content: Textual content of the message.
        timestamp: Message creation UTC timestamp.
        metadata: Additional metadata dictionary.
    """

    message_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique message identifier string.",
    )
    role: str = Field(
        ...,
        description="Message role (e.g. 'user', 'assistant', 'system').",
    )
    content: str = Field(
        ...,
        description="Text content of the message.",
    )
    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="Message creation UTC timestamp.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional key-value metadata dictionary.",
    )


class SessionData(BaseModel):
    """Session state model storing conversation history, context, and TTL timestamps.

    Attributes:
        session_id: Unique session identifier string.
        user_id: Optional user identifier string.
        created_at: Creation UTC timestamp.
        updated_at: Last update UTC timestamp.
        expires_at: Optional expiration UTC timestamp.
        context: Custom key-value context dictionary.
        history: Sequence of conversation messages.
    """

    session_id: str = Field(
        ...,
        description="Unique session identifier string.",
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user identifier string.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="Creation UTC timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="Last update UTC timestamp.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration UTC timestamp.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom key-value context dictionary.",
    )
    history: list[SessionMessage] = Field(
        default_factory=list,
        description="Sequence of conversation messages.",
    )

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if session is expired relative to current time.

        Args:
            now: Optional current timestamp override.

        Returns:
            bool: True if session is expired, False otherwise.
        """
        if self.expires_at is None:
            return False
        current_time = now or _utc_now()
        return current_time >= self.expires_at
