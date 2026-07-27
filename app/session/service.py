"""Session Management Service Layer.

High-level application service orchestrating session state, context, and conversation history.
"""

import logging
from typing import Any

from app.services.base import BaseService
from app.session.base import BaseSessionStore
from app.session.models import SessionData, SessionMessage
from app.session.store import InMemorySessionStore

logger = logging.getLogger(__name__)


class SessionService(BaseService):
    """High-level application service orchestrating session state and history."""

    def __init__(self, store: BaseSessionStore | None = None) -> None:
        """Initialize SessionService with an injected store or default InMemorySessionStore.

        Args:
            store: Optional BaseSessionStore implementation.
        """
        self._store = store or InMemorySessionStore()
        logger.info("SessionService initialized")

    async def create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        ttl_seconds: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> SessionData:
        """Create a new session.

        Args:
            session_id: Optional custom session ID.
            user_id: Optional user identifier.
            ttl_seconds: Optional custom TTL override.
            context: Optional initial session context dictionary.

        Returns:
            SessionData: Created session instance.
        """
        return await self._store.create_session(
            session_id=session_id,
            user_id=user_id,
            ttl_seconds=ttl_seconds,
            context=context,
        )

    async def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve an active session by ID.

        Args:
            session_id: Session identifier string.

        Returns:
            SessionData | None: Active session model or None.
        """
        return await self._store.get_session(session_id)

    async def get_or_create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> SessionData:
        """Retrieve an existing session or create a new one if missing/expired.

        Args:
            session_id: Optional session identifier string.
            user_id: Optional user identifier string.

        Returns:
            SessionData: Active or newly created session model.
        """
        if session_id:
            session = await self.get_session(session_id)
            if session:
                return session

        return await self.create_session(session_id=session_id, user_id=user_id)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SessionData:
        """Add a message with a specific role to session history.

        Args:
            session_id: Target session ID.
            role: Message role string (e.g. 'user', 'assistant', 'system', 'tool', 'planner', 'function').
            content: Textual content of the message.
            metadata: Optional metadata dictionary.

        Returns:
            SessionData: Updated session model.
        """
        msg = SessionMessage(role=role, content=content, metadata=metadata or {})
        return await self._store.append_message(session_id, msg)

    async def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SessionData:
        """Add a user role message to session history.

        Args:
            session_id: Target session ID.
            content: User message text.
            metadata: Optional metadata dictionary.

        Returns:
            SessionData: Updated session model.
        """
        return await self.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata,
        )

    async def add_assistant_message(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> SessionData:
        """Add an assistant role message to session history.

        Args:
            session_id: Target session ID.
            content: Assistant message text.
            metadata: Optional metadata dictionary.

        Returns:
            SessionData: Updated session model.
        """
        return await self.add_message(
            session_id=session_id,
            role="assistant",
            content=content,
            metadata=metadata,
        )

    async def get_history(self, session_id: str) -> list[SessionMessage]:
        """Retrieve conversation message history for a session.

        Args:
            session_id: Session identifier string.

        Returns:
            list[SessionMessage]: Sequence of stored conversation messages.
        """
        session = await self.get_session(session_id)
        return session.history if session else []

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: Session identifier string.

        Returns:
            bool: True if deleted, False otherwise.
        """
        return await self._store.delete_session(session_id)

    async def cleanup_expired(self) -> int:
        """Purge all expired sessions from store.

        Returns:
            int: Number of purged expired sessions.
        """
        return await self._store.clear_expired()

    async def health_check(self) -> bool:
        """Check operational health status of session store.

        Returns:
            bool: True if store is healthy and operational.
        """
        return True

    async def close(self) -> None:
        """Close underlying session store."""
        await self._store.close()
