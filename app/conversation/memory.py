"""Conversation Memory module for MantraSetu AgentOS.

This module implements ConversationMemory for managing in-memory chronological conversation turn history per session in a thread-safe manner.
"""

from __future__ import annotations

import asyncio
from uuid import UUID

from app.conversation.base import (
    BaseConversationMemory,
    ConversationInitializationError,
    ConversationMemoryError,
)
from app.conversation.models import ConversationTurn


class ConversationMemory(BaseConversationMemory):
    """Thread-safe conversation history storage implementing BaseConversationMemory.

    Responsibility:
        Manages chronological persistence, retrieval, and clearing of ConversationTurn objects
        associated with session identifiers without managing session lifecycles, AI prompts, or browser operations.
    """

    def __init__(self) -> None:
        """Initialize ConversationMemory with internal history registry and thread-safe lock."""
        self._history: dict[UUID, tuple[ConversationTurn, ...]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the memory component has been initialized.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
        """
        if not self._initialized:
            raise ConversationInitializationError(
                "ConversationMemory is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize memory storage runtime state.

        Idempotent initialization: safely returns if already initialized without clearing stored history.
        """
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close memory storage, clear all recorded history, and release resources."""
        async with self._lock:
            self._history.clear()
            self._initialized = False

    async def save_turn(self, session_id: UUID, turn: ConversationTurn) -> None:
        """Append a ConversationTurn to the session history in chronological order.

        Args:
            session_id: Unique session identifier UUID.
            turn: ConversationTurn model instance to record.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationMemoryError: If turn parameter is missing or invalid.
        """
        self._require_initialized()
        if not turn:
            raise ConversationMemoryError("Cannot save empty or None ConversationTurn.")

        async with self._lock:
            existing_turns = self._history.get(session_id, ())
            self._history[session_id] = existing_turns + (turn,)

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

        Raises:
            ConversationInitializationError: If memory is uninitialized.
            ConversationMemoryError: If limit parameter is negative.
        """
        self._require_initialized()
        if limit is not None and limit <= 0:
            raise ConversationMemoryError("Limit parameter must be a positive integer.")

        async with self._lock:
            turns = self._history.get(session_id, ())
            if limit is not None and len(turns) > limit:
                return turns[-limit:]
            return turns

    async def clear_memory(self, session_id: UUID) -> None:
        """Purge all recorded conversation turns for a session.

        Args:
            session_id: Unique session identifier UUID to clear.

        Raises:
            ConversationInitializationError: If memory is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            self._history.pop(session_id, None)

    async def health_check(self) -> bool:
        """Check operational health of the memory component.

        Returns:
            bool: True if initialized and functional, False otherwise.
        """
        return self._initialized
