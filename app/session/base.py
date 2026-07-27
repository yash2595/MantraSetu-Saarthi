"""Abstract Base Storage interface for Session Management.

Defines the contract that all session storage providers (InMemory, Redis, DB)
must implement.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.session.models import SessionData, SessionMessage


class BaseSessionStore(ABC):
    """Abstract base class contract for all Session Storage providers."""

    @abstractmethod
    async def create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        ttl_seconds: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> SessionData:
        """Create and store a new session.

        Args:
            session_id: Optional custom session ID.
            user_id: Optional user identifier.
            ttl_seconds: Optional TTL override in seconds.
            context: Optional initial session context dictionary.

        Returns:
            SessionData: Created session state model.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve a session by its unique ID, returning None if expired or not found.

        Args:
            session_id: Unique session identifier string.

        Returns:
            SessionData | None: Active session data or None if missing/expired.
        """
        raise NotImplementedError

    @abstractmethod
    async def save_session(self, session: SessionData) -> None:
        """Save or update an existing session state.

        Args:
            session: SessionData model to persist.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: Unique session identifier string.

        Returns:
            bool: True if deleted, False if session did not exist.
        """
        raise NotImplementedError

    @abstractmethod
    async def append_message(
        self,
        session_id: str,
        message: SessionMessage,
    ) -> SessionData:
        """Append a message to session history.

        Args:
            session_id: Target session ID.
            message: SessionMessage instance to append.

        Returns:
            SessionData: Updated session state model.
        """
        raise NotImplementedError

    @abstractmethod
    async def clear_expired(self) -> int:
        """Prune all expired sessions.

        Returns:
            int: Number of expired sessions purged.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Release underlying storage connection resources."""
        raise NotImplementedError
