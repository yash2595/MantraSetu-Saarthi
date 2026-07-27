"""Conversation Manager coordinator for MantraSetu AgentOS.

This module implements ConversationManager for coordinating conversation session lifecycle operations
and memory turn storage through public abstract contracts without accessing private component attributes.
"""

from __future__ import annotations

from uuid import UUID

from app.conversation.base import (
    BaseConversationManager,
    BaseConversationMemory,
    BaseConversationSession,
    ConversationClosedError,
    ConversationInitializationError,
    ConversationNotFoundError,
    ConversationValidationError,
)
from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
    ConversationSession,
    ConversationStatus,
    ConversationTurn,
)


class ConversationManager(BaseConversationManager):
    """Coordinator service implementing BaseConversationManager.

    Responsibility:
        Coordinates session verification, message handling, turn creation, context updates,
        and turn persistence by delegating strictly through public BaseConversationSession and
        BaseConversationMemory contracts without accessing internal private data structures.
    """

    def __init__(
        self,
        session_manager: BaseConversationSession,
        memory: BaseConversationMemory,
    ) -> None:
        """Initialize ConversationManager with session manager and memory dependencies.

        Args:
            session_manager: BaseConversationSession instance.
            memory: BaseConversationMemory instance.
        """
        self._session_manager = session_manager
        self._memory = memory
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the conversation manager has been initialized.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationManager is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize underlying session manager and memory components."""
        await self._session_manager.initialize()
        await self._memory.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close underlying memory and session manager components."""
        await self._memory.close()
        await self._session_manager.close()
        self._initialized = False

    async def health_check(self) -> bool:
        """Check aggregated operational health across session manager and memory.

        Returns:
            bool: True if initialized and both session manager and memory report healthy, False otherwise.
        """
        if not self._initialized:
            return False

        session_healthy = await self._session_manager.health_check()
        memory_healthy = await self._memory.health_check()
        return session_healthy and memory_healthy

    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new conversation session by delegating to session manager.

        Args:
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created session model.
        """
        self._require_initialized()
        return await self._session_manager.create_session(context)

    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session instance if found, None otherwise.
        """
        self._require_initialized()
        return await self._session_manager.get_session(session_id)

    async def close_session(self, session_id: UUID) -> None:
        """Close a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        self._require_initialized()
        await self._session_manager.close_session(session_id)

    async def add_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> ConversationTurn:
        """Add a message to an active session, construct a turn, and save to memory.

        Args:
            session_id: Target session identifier UUID.
            message: ConversationMessage command model.

        Returns:
            ConversationTurn: Constructed conversation turn model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationNotFoundError: If session does not exist.
            ConversationClosedError: If session is archived or closed.
            ConversationValidationError: If message is invalid.
        """
        self._require_initialized()
        if not message:
            raise ConversationValidationError("Message cannot be None.")

        session = await self._session_manager.get_session(session_id)
        if not session:
            raise ConversationNotFoundError(f"Conversation session {session_id} not found.")

        if session.status != ConversationStatus.ACTIVE:
            raise ConversationClosedError(
                f"Conversation session {session_id} is in '{session.status}' status (must be ACTIVE)."
            )

        turn = ConversationTurn(user_message=message)
        await self._memory.save_turn(session_id, turn)

        return turn

    async def update_context(
        self,
        session_id: UUID,
        context: ConversationContext,
    ) -> ConversationContext:
        """Update context settings for an active conversation session using public contract.

        Args:
            session_id: Target session identifier UUID.
            context: ConversationContext instance.

        Returns:
            ConversationContext: Updated context model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationNotFoundError: If session does not exist.
            ConversationClosedError: If session is archived or closed.
            ConversationValidationError: If context is invalid.
        """
        self._require_initialized()
        if not context:
            raise ConversationValidationError("Context cannot be None.")

        session = await self._session_manager.get_session(session_id)
        if not session:
            raise ConversationNotFoundError(f"Conversation session {session_id} not found.")

        if session.status != ConversationStatus.ACTIVE:
            raise ConversationClosedError(
                f"Conversation session {session_id} is in '{session.status}' status (must be ACTIVE)."
            )

        return await self._session_manager.update_context(session_id, context)

    async def get_context(self, session_id: UUID) -> ConversationContext:
        """Retrieve context settings for a conversation session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active session context model.

        Raises:
            ConversationInitializationError: If manager is uninitialized.
            ConversationNotFoundError: If session does not exist.
        """
        self._require_initialized()
        session = await self._session_manager.get_session(session_id)
        if not session:
            raise ConversationNotFoundError(f"Conversation session {session_id} not found.")

        return session.context
