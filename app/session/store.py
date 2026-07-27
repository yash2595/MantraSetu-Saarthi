"""In-Memory Thread-Safe Session Store implementation.

Provides an async, thread-safe in-memory session store supporting TTL expiration.
"""

import asyncio
import logging
from datetime import timedelta
from typing import Any
from uuid import uuid4

from app.core.exceptions import NotFoundError
from app.session.base import BaseSessionStore
from app.session.models import SessionData, SessionMessage, _utc_now
from app.session.settings import SessionSettings, session_settings

logger = logging.getLogger(__name__)


class InMemorySessionStore(BaseSessionStore):
    """Thread-safe, async in-memory session store supporting TTL expiration."""

    def __init__(self, settings: SessionSettings | None = None) -> None:
        """Initialize in-memory store with async lock.

        Args:
            settings: Optional custom SessionSettings override.
        """
        self._settings = settings or session_settings
        self._sessions: dict[str, SessionData] = {}
        self._lock = asyncio.Lock()
        logger.info(
            "InMemorySessionStore initialized [ttl=%ds]", self._settings.ttl_seconds
        )

    async def create_session(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        ttl_seconds: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> SessionData:
        """Create and persist a new SessionData instance.

        Args:
            session_id: Optional custom session ID.
            user_id: Optional user identifier.
            ttl_seconds: Optional TTL override in seconds.
            context: Optional initial session context dictionary.

        Returns:
            SessionData: Created session state model.
        """
        async with self._lock:
            sid = (
                session_id.strip()
                if session_id and session_id.strip()
                else str(uuid4())
            )
            effective_ttl = (
                ttl_seconds if ttl_seconds is not None else self._settings.ttl_seconds
            )

            now = _utc_now()
            expires_at = (
                now + timedelta(seconds=effective_ttl) if effective_ttl > 0 else None
            )

            session = SessionData(
                session_id=sid,
                user_id=user_id,
                created_at=now,
                updated_at=now,
                expires_at=expires_at,
                context=context or {},
                history=[],
            )

            self._sessions[sid] = session
            logger.info("Session created [session_id=%s, ttl=%s]", sid, effective_ttl)
            return session

    async def get_session(self, session_id: str) -> SessionData | None:
        """Retrieve active session by ID, purging if expired.

        Args:
            session_id: Unique session identifier string.

        Returns:
            SessionData | None: Active session data or None.
        """
        async with self._lock:
            if not session_id or session_id not in self._sessions:
                return None

            session = self._sessions[session_id]
            if session.is_expired():
                logger.info("Session expired and purged [session_id=%s]", session_id)
                del self._sessions[session_id]
                return None

            return session

    async def save_session(self, session: SessionData) -> None:
        """Save or update session in store.

        Args:
            session: SessionData model to update.
        """
        async with self._lock:
            session.updated_at = _utc_now()
            self._sessions[session.session_id] = session
            logger.debug("Session updated [session_id=%s]", session.session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from store.

        Args:
            session_id: Unique session identifier string.

        Returns:
            bool: True if deleted, False if session was not found.
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info("Session deleted [session_id=%s]", session_id)
                return True
            return False

    async def append_message(
        self,
        session_id: str,
        message: SessionMessage,
    ) -> SessionData:
        """Append message to session history maintaining max history length.

        Args:
            session_id: Target session ID.
            message: SessionMessage instance to append.

        Returns:
            SessionData: Updated session state.

        Raises:
            NotFoundError: If session does not exist or has expired.
        """
        async with self._lock:
            if session_id not in self._sessions:
                raise NotFoundError(f"Session '{session_id}' not found.")

            session = self._sessions[session_id]
            if session.is_expired():
                del self._sessions[session_id]
                raise NotFoundError(f"Session '{session_id}' has expired.")

            session.history.append(message)
            if len(session.history) > self._settings.max_history_length:
                session.history = session.history[-self._settings.max_history_length :]

            session.updated_at = _utc_now()
            if self._settings.ttl_seconds > 0:
                session.expires_at = session.updated_at + timedelta(
                    seconds=self._settings.ttl_seconds
                )

            self._sessions[session_id] = session
            logger.debug(
                "Message appended to session [session_id=%s, history_len=%d]",
                session_id,
                len(session.history),
            )
            return session

    async def clear_expired(self) -> int:
        """Clear all expired sessions.

        Returns:
            int: Number of purged expired sessions.
        """
        async with self._lock:
            now = _utc_now()
            expired_ids = [
                sid for sid, s in self._sessions.items() if s.is_expired(now)
            ]
            for sid in expired_ids:
                del self._sessions[sid]

            if expired_ids:
                logger.info("Expired sessions purged [count=%d]", len(expired_ids))
            return len(expired_ids)

    async def close(self) -> None:
        """Clear store on shutdown."""
        async with self._lock:
            self._sessions.clear()
            logger.info("InMemorySessionStore closed")
