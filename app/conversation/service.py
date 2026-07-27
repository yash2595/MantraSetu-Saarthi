"""Conversation Service facade module for MantraSetu AgentOS.

This module provides ConversationService as the primary public entry point for the Conversation subsystem,
delegating all session management, message handling, context configuration, and history turn operations
to BaseConversationManager without embedding business logic or data storage.
"""

from __future__ import annotations

from uuid import UUID

from app.conversation.base import BaseConversationEngine, BaseConversationManager
from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
    ConversationSession,
    ConversationTurn,
)


class ConversationService(BaseConversationEngine):
    """Public facade service implementing BaseConversationEngine.

    Responsibility:
        Exposes a clean subsystem facade API to external consumers. Delegates all operations
        strictly to the injected BaseConversationManager implementation.
    """

    def __init__(self, manager: BaseConversationManager) -> None:
        """Initialize ConversationService with an injected BaseConversationManager dependency.

        Args:
            manager: BaseConversationManager instance coordinating session and memory.
        """
        self._manager = manager

    async def initialize(self) -> None:
        """Initialize the conversation service and underlying manager dependencies."""
        await self._manager.initialize()

    async def close(self) -> None:
        """Close and release all manager and component resources."""
        await self._manager.close()

    async def health_check(self) -> bool:
        """Check operational health of the conversation subsystem.

        Returns:
            bool: True if the underlying manager reports healthy, False otherwise.
        """
        return await self._manager.health_check()

    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new managed conversation session.

        Args:
            context: Optional ConversationContext configuration instance.

        Returns:
            ConversationSession: Created session entity.
        """
        return await self._manager.create_session(context)

    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a managed conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session model if found, None otherwise.
        """
        return await self._manager.get_session(session_id)

    async def close_session(self, session_id: UUID) -> None:
        """Close and archive a managed conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        await self._manager.close_session(session_id)

    async def add_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> ConversationTurn:
        """Add a message to a conversation session and return the resulting turn.

        Args:
            session_id: Target session identifier UUID.
            message: ConversationMessage model instance.

        Returns:
            ConversationTurn: Created or updated conversation turn.
        """
        return await self._manager.add_message(session_id, message)

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update context settings for an active conversation session.

        Args:
            session_id: Target session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated context model.
        """
        return await self._manager.update_context(session_id, context)

    async def get_context(self, session_id: UUID) -> ConversationContext:
        """Retrieve context settings for a conversation session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active session context model.
        """
        return await self._manager.get_context(session_id)
