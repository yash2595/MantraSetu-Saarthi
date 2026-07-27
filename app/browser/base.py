"""Abstract contracts and interfaces for the Browser automation subsystem in MantraSetu AgentOS.

This module defines abstract base classes for browser session management, action execution,
and engine orchestration alongside domain exception hierarchies, enforcing Dependency Inversion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.browser.models import (
    BaseBrowserModel,
    BrowserAction,
    BrowserBatch,
    BrowserResult,
    BrowserSession,
    _utc_now,
)


class BrowserRuntimeHandle(BaseBrowserModel):
    """Public framework-independent handle representing active runtime browser handles.

    Attributes:
        session_id: Unique session identifier UUID.
        browser: Placeholder for active browser instance.
        context: Placeholder for active browser context instance.
        page: Placeholder for active page instance.
        created_at: UTC timestamp when the handle was created.
    """

    session_id: UUID
    browser: Any | None = None
    context: Any | None = None
    page: Any | None = None


class BrowserError(Exception):
    """Base exception for all browser subsystem errors."""

    pass


class BrowserSessionError(BrowserError):
    """Base exception raised for session management errors."""

    pass


class SessionNotFoundError(BrowserSessionError):
    """Raised when a requested browser session cannot be found."""

    pass


class BrowserExecutionError(BrowserError):
    """Base exception raised for action or batch execution failures."""

    pass


class ActionExecutionError(BrowserExecutionError):
    """Raised when an individual browser action fails to execute."""

    pass


class BatchExecutionError(BrowserExecutionError):
    """Raised when a batch of browser actions fails to execute completely."""

    pass


class BaseBrowserSession(ABC):
    """Abstract interface defining the contract for browser session lifecycle management.

    Responsibility:
        Establishes session initialization, creation, retrieval, listing, health monitoring,
        runtime handle access, and closure operations.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize session manager resources and background processes."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close session manager resources and terminate active sessions."""
        ...

    @abstractmethod
    async def create_session(
        self,
        user_agent: str | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> BrowserSession:
        """Create and initialize a new browser session instance.

        Args:
            user_agent: Optional User-Agent header string.
            viewport_width: Viewport width in pixels.
            viewport_height: Viewport height in pixels.

        Returns:
            BrowserSession: Created browser session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> BrowserSession | None:
        """Retrieve an active or stored browser session by its identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserSession | None: Session instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_runtime_handle(self, session_id: UUID) -> BrowserRuntimeHandle | None:
        """Retrieve the public runtime handle for an active browser session.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserRuntimeHandle | None: Runtime handle if active, None otherwise.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> None:
        """Close and release an active browser session.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        ...

    @abstractmethod
    async def list_sessions(self) -> tuple[BrowserSession, ...]:
        """List all active and managed browser sessions.

        Returns:
            tuple[BrowserSession, ...]: Immutable tuple of active BrowserSession objects.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check the operational health of the session manager.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...


class BaseBrowserExecutor(ABC):
    """Abstract interface defining the contract for executing browser actions and batches.

    Responsibility:
        Handles execution of single browser actions, action batches, cancellation,
        and execution health checks.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize executor driver dependencies and resources."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close executor driver dependencies and release resources."""
        ...

    @abstractmethod
    async def execute_action(
        self,
        session_id: UUID,
        action: BrowserAction,
    ) -> BrowserResult:
        """Execute a single browser action command within a session context.

        Args:
            session_id: Target session identifier UUID.
            action: BrowserAction command to execute.

        Returns:
            BrowserResult: Execution outcome result model.
        """
        ...

    @abstractmethod
    async def execute_batch(
        self,
        session_id: UUID,
        batch: BrowserBatch,
    ) -> tuple[BrowserResult, ...]:
        """Execute a batch sequence of browser actions within a session context.

        Args:
            session_id: Target session identifier UUID.
            batch: BrowserBatch sequence of actions to execute.

        Returns:
            tuple[BrowserResult, ...]: Immutable tuple of execution results for each action.
        """
        ...

    @abstractmethod
    async def cancel(self, session_id: UUID) -> None:
        """Cancel ongoing action or batch execution for a given session.

        Args:
            session_id: Unique session identifier UUID to cancel.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational availability and driver health of the executor.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...


class BaseBrowserEngine(ABC):
    """Abstract top-level interface defining the complete Browser Engine contract.

    Responsibility:
        Combines session lifecycle management and action execution capabilities into a unified facade.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the browser engine runtime components."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close and release all engine session and executor resources."""
        ...

    @abstractmethod
    async def create_session(
        self,
        user_agent: str | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> BrowserSession:
        """Create a new browser session managed by the engine.

        Args:
            user_agent: Optional User-Agent string.
            viewport_width: Viewport width in pixels.
            viewport_height: Viewport height in pixels.

        Returns:
            BrowserSession: Created session entity.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: UUID) -> BrowserSession | None:
        """Retrieve a managed browser session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserSession | None: Session entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: UUID) -> None:
        """Close a managed browser session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        ...

    @abstractmethod
    async def execute_action(
        self,
        session_id: UUID,
        action: BrowserAction,
    ) -> BrowserResult:
        """Execute a browser action command within the specified session.

        Args:
            session_id: Target session identifier UUID.
            action: BrowserAction command to execute.

        Returns:
            BrowserResult: Execution outcome result model.
        """
        ...

    @abstractmethod
    async def execute_batch(
        self,
        session_id: UUID,
        batch: BrowserBatch,
    ) -> tuple[BrowserResult, ...]:
        """Execute a batch sequence of browser actions within the specified session.

        Args:
            session_id: Target session identifier UUID.
            batch: BrowserBatch sequence to execute.

        Returns:
            tuple[BrowserResult, ...]: Tuple of execution results.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health of the overall browser engine.

        Returns:
            bool: True if engine components are healthy, False otherwise.
        """
        ...
