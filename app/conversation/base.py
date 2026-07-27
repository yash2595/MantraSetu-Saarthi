"""Abstract contracts and interfaces for the Conversation subsystem in MantraSetu AgentOS.

This module defines abstract base classes for session management, conversation memory,
manager coordination, and engine facade contracts alongside domain exception hierarchies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.conversation.models import (
    ConversationContext,
    ConversationMessage,
    ConversationSession,
    ConversationTurn,
)


class ConversationError(Exception):
    """Base exception for all conversation subsystem errors."""

    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a requested conversation session or resource cannot be found."""

    pass


class ConversationClosedError(ConversationError):
    """Raised when attempting an operation on a closed conversation session."""

    pass


class ConversationMemoryError(ConversationError):
    """Raised when memory storage or retrieval operations fail."""

    pass


class ConversationContextError(ConversationError):
    """Raised when conversation context validation or updates fail."""

    pass


class ConversationValidationError(ConversationError):
    """Raised when message or turn parameter validation fails."""

    pass


class ConversationInitializationError(ConversationError):
    """Raised when component initialization fails."""

    pass


class BaseConversationSession(ABC):
    """Abstract interface defining the contract for conversation session lifecycle management."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize session manager resources and state."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close session manager and release allocated resources."""
        ...

    @abstractmethod
    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create and register a new conversation session instance.

        Args:
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created conversation session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session instance if found, None otherwise.
        """
        ...

    @abstractmethod
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
            ConversationContext: Updated conversation context entity.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> None:
        """Close and archive a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        ...

    @abstractmethod
    async def list_sessions(self) -> tuple[ConversationSession, ...]:
        """List all active and managed conversation sessions.

        Returns:
            tuple[ConversationSession, ...]: Immutable tuple of ConversationSession objects.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health of the session manager.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...


class BaseConversationMemory(ABC):
    """Abstract interface defining the contract for conversation history and memory storage."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize memory storage resources."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close memory storage resources."""
        ...

    @abstractmethod
    async def save_turn(self, session_id: UUID, turn: ConversationTurn) -> None:
        """Persist a conversation turn for a session.

        Args:
            session_id: Unique session identifier UUID.
            turn: ConversationTurn instance to record.
        """
        ...

    @abstractmethod
    async def get_turns(
        self,
        session_id: UUID,
        limit: int | None = None,
    ) -> tuple[ConversationTurn, ...]:
        """Retrieve chronological conversation turns for a session.

        Args:
            session_id: Unique session identifier UUID.
            limit: Optional maximum number of recent turns to retrieve.

        Returns:
            tuple[ConversationTurn, ...]: Immutable tuple of ConversationTurn objects.
        """
        ...

    @abstractmethod
    async def clear_memory(self, session_id: UUID) -> None:
        """Purge all stored conversation turns for a session.

        Args:
            session_id: Unique session identifier UUID to clear.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health of the memory storage component.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...


class BaseConversationManager(ABC):
    """Abstract interface defining the contract for conversation message and context coordination."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize manager component resources."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close manager component resources."""
        ...

    @abstractmethod
    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new managed conversation session by delegating to session manager.

        Args:
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> None:
        """Close a conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        ...

    @abstractmethod
    async def add_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> ConversationTurn:
        """Add a message to an active conversation session and update state.

        Args:
            session_id: Unique session identifier UUID.
            message: ConversationMessage command instance.

        Returns:
            ConversationTurn: Created or updated conversation turn.
        """
        ...

    @abstractmethod
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
            ConversationContext: Updated conversation context entity.
        """
        ...

    @abstractmethod
    async def get_context(self, session_id: UUID) -> ConversationContext:
        """Retrieve active conversation context settings for a session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationContext: Active conversation context entity.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health of the manager component.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...


class BaseConversationEngine(ABC):
    """Abstract top-level interface defining the complete Conversation Engine facade contract."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize conversation engine runtime components."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close and release all conversation engine components."""
        ...

    @abstractmethod
    async def create_session(
        self,
        context: ConversationContext | None = None,
    ) -> ConversationSession:
        """Create a new managed conversation session.

        Args:
            context: Optional ConversationContext configuration.

        Returns:
            ConversationSession: Created session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> ConversationSession | None:
        """Retrieve a managed conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            ConversationSession | None: Session entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> None:
        """Close a managed conversation session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        ...

    @abstractmethod
    async def add_message(
        self,
        session_id: UUID,
        message: ConversationMessage,
    ) -> ConversationTurn:
        """Add a message to a conversation session and return the resulting turn.

        Args:
            session_id: Target session identifier UUID.
            message: ConversationMessage to process.

        Returns:
            ConversationTurn: Resulting conversation turn.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health of the overall conversation engine.

        Returns:
            bool: True if engine components are healthy, False otherwise.
        """
        ...
