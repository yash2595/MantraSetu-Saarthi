"""Browser Subsystem Service Facade for MantraSetu AgentOS.

This module provides the BrowserService class as the primary entry point for the Browser subsystem,
wiring together BrowserRegistry, BrowserSessionManager, BrowserExecutor, and BrowserController
via dependency injection without performing browser automation directly.
"""

from __future__ import annotations

from uuid import UUID

from app.browser.base import (
    BaseBrowserEngine,
    BaseBrowserExecutor,
    BaseBrowserSession,
    BrowserError,
)
from app.browser.controller import BrowserController
from app.browser.models import (
    BrowserAction,
    BrowserBatch,
    BrowserResult,
    BrowserSession,
)
from app.browser.registry import BrowserRegistry


class BrowserService(BaseBrowserEngine):
    """Subsystem facade implementing BaseBrowserEngine contract.

    Responsibility:
        Composes and exposes the Browser subsystem. Resolves provider session managers and executors
        from BrowserRegistry, delegates session lifecycle calls to BaseBrowserSession, and delegates
        action/batch execution calls to BrowserController.
    """

    def __init__(self, registry: BrowserRegistry) -> None:
        """Initialize BrowserService with an injected BrowserRegistry.

        Args:
            registry: BrowserRegistry instance holding registered provider implementations.
        """
        self._registry = registry
        self._session_manager: BaseBrowserSession | None = None
        self._executor: BaseBrowserExecutor | None = None
        self._controller: BrowserController | None = None
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the browser service has been initialized.

        Raises:
            BrowserError: If initialize() has not been called.
        """
        if not self._initialized or not self._session_manager or not self._controller:
            raise BrowserError(
                "BrowserService is not initialized. Call initialize(provider) first."
            )

    async def initialize(self, provider: str = "default") -> None:
        """Initialize the subsystem for a specified provider.

        Resolves the provider session manager and executor from BrowserRegistry, constructs the
        BrowserController, and initializes all component resources.

        Args:
            provider: Registered provider identifier string (e.g. 'playwright', 'mock').

        Raises:
            BrowserError: If provider resolution or component initialization fails.
        """
        self._session_manager = await self._registry.get_session_manager(provider)
        self._executor = await self._registry.get_executor(provider)

        self._controller = BrowserController(
            session_manager=self._session_manager,
            executor=self._executor,
        )

        await self._controller.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close and gracefully release all subsystem controller, executor, and session resources."""
        if self._controller:
            await self._controller.close()
            self._controller = None

        self._executor = None
        self._session_manager = None
        self._initialized = False

    async def health_check(self) -> bool:
        """Check operational health across the service and controller hierarchy.

        Returns:
            bool: True if initialized and controller health check passes, False otherwise.
        """
        if not self._initialized or not self._controller:
            return False
        return await self._controller.health_check()

    async def create_session(
        self,
        user_agent: str | None = None,
        viewport_width: int = 1280,
        viewport_height: int = 720,
    ) -> BrowserSession:
        """Create a new browser session via the session manager.

        Args:
            user_agent: Optional User-Agent string.
            viewport_width: Viewport width in pixels.
            viewport_height: Viewport height in pixels.

        Returns:
            BrowserSession: Created session entity.
        """
        self._require_initialized()
        assert self._session_manager is not None
        return await self._session_manager.create_session(
            user_agent=user_agent,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

    async def get_session(self, session_id: UUID) -> BrowserSession | None:
        """Retrieve a managed browser session by identifier.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserSession | None: Session model if found, None otherwise.
        """
        self._require_initialized()
        assert self._session_manager is not None
        return await self._session_manager.get_session(session_id)

    async def close_session(self, session_id: UUID) -> None:
        """Close a managed browser session by identifier.

        Args:
            session_id: Unique session identifier UUID to close.
        """
        self._require_initialized()
        assert self._session_manager is not None
        await self._session_manager.close_session(session_id)

    async def list_sessions(self) -> tuple[BrowserSession, ...]:
        """List all managed browser session instances.

        Returns:
            tuple[BrowserSession, ...]: Immutable tuple of BrowserSession models.
        """
        self._require_initialized()
        assert self._session_manager is not None
        return await self._session_manager.list_sessions()

    async def execute_action(
        self,
        session_id: UUID,
        action: BrowserAction,
    ) -> BrowserResult:
        """Delegate action execution to BrowserController.

        Args:
            session_id: Target session identifier UUID.
            action: BrowserAction command model.

        Returns:
            BrowserResult: Execution outcome result model.
        """
        self._require_initialized()
        assert self._controller is not None
        return await self._controller.execute_action(session_id, action)

    async def execute_batch(
        self,
        session_id: UUID,
        batch: BrowserBatch,
    ) -> tuple[BrowserResult, ...]:
        """Delegate batch action sequence execution to BrowserController.

        Args:
            session_id: Target session identifier UUID.
            batch: BrowserBatch command model sequence.

        Returns:
            tuple[BrowserResult, ...]: Tuple of execution results for each action.
        """
        self._require_initialized()
        assert self._controller is not None
        return await self._controller.execute_batch(session_id, batch)
