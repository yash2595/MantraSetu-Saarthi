"""Conversation Session Manager module for MantraSetu AgentOS.

This module implements ConversationSessionManager for managing conversation session lifecycles,
thread-safe registration, context assignment, and session status transitions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from app.conversation.base import (
    BaseConversationSession,
    ConversationClosedError,
    ConversationInitializationError,
    ConversationNotFoundError,
)
from app.conversation.models import (
    ConversationContext,
    ConversationSession,
    ConversationStatus,
)


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class ConversationSessionManager(BaseConversationSession):
    """Thread-safe conversation session manager implementing BaseConversationSession.

    Responsibility:
        Manages creation, retrieval, listing, status updating, and archiving of ConversationSession
        objects without embedding AI prompt logic, browser automation, or memory storage.
    """

    def __init__(self) -> None:
        """Initialize ConversationSessionManager with internal registry and thread-safe lock."""
        self._sessions: dict[UUID, ConversationSession] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the session manager has been initialized.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationSessionManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize session manager runtime state.

        Idempotent initialization: safely returns if already initialized without recreating registry.
        """
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close all managed conversation sessions, archive active sessions, and clear registry."""
        async with self._lock:
            for sid, session in list(self._sessions.items()):
                if session.status == ConversationStatus.ACTIVE:
                    self._sessions[sid] = session.model_copy(
                        update={
                            "status": ConversationStatus.ARCHIVED,
                            "updated_at": _utc_now(),
                        }
                    )

            self._sessions.clear()
            self._initialized = False

    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create and register a new thread-safe ConversationSession.

        Args:
            context: Optional ConversationContext configuration instance.

        Returns:
            ConversationSession: Created conversation session model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            session = ConversationSession(
                status=ConversationStatus.ACTIVE,
                context=context or ConversationContext(),
            )
            self._sessions[session.session_id] = session
            return session

    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session model if found, None otherwise.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return self._sessions.get(session_id)

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update active conversation context settings for a session.

        Args:
            session_id: Unique session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated conversation context model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationNotFoundError: If session does not exist.
            ConversationClosedError: If session is archived or closed.
        """
        self._require_initialized()
        async with self._lock:
            if session_id not in self._sessions:
                raise ConversationNotFoundError(
                    f"Conversation session {session_id} does not exist."
                )

            existing = self._sessions[session_id]
            if existing.status in (ConversationStatus.ARCHIVED, ConversationStatus.COMPLETED):
                raise ConversationClosedError(
                    f"Conversation session {session_id} is already closed or archived."
                )

            updated = existing.model_copy(
                update={
                    "context": context,
                    "updated_at": _utc_now(),
                }
            )
            self._sessions[session_id] = updated
            return context

    async def close_session(self, session_id: UUID) -> None:
        """Close and archive a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.

        Raises:
            ConversationNotFoundError: If the session is not registered.
            ConversationClosedError: If the session is already archived or closed.
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            if session_id not in self._sessions:
                raise ConversationNotFoundError(
                    f"Conversation session {session_id} does not exist."
                )

            existing = self._sessions[session_id]
            if existing.status in (ConversationStatus.ARCHIVED, ConversationStatus.COMPLETED):
                raise ConversationClosedError(
                    f"Conversation session {session_id} is already closed or archived."
                )

            closed_session = existing.model_copy(
                update={
                    "status": ConversationStatus.ARCHIVED,
                    "updated_at": _utc_now(),
                }
            )
            self._sessions[session_id] = closed_session

    async def list_sessions(self) -> tuple[ConversationSession, ...]:
        """List all managed conversation session instances.

        Returns:
            tuple[ConversationSession, ...]: Immutable tuple of ConversationSession objects.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            return tuple(self._sessions.values())

    async def health_check(self) -> bool:
        """Check operational health of the session manager.

        Returns:
            bool: True if initialized and functional, False otherwise.
        """
        return self._initialized
