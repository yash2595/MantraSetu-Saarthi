"""FastAPI application factory with AI subsystem lifecycle integration.

Creates and configures the FastAPI application instance and wires the full AI
subsystem startup/shutdown sequence through the existing LifecycleManager.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.dependency import ApplicationContainer
from app.core.lifecycle import BaseLifecycleService, LifecycleManager
from app.core.logging import configure_logging
from app.core.settings import ApplicationSettings


# ---------------------------------------------------------------------------
# Lifecycle service adapters
# Each wraps one composition-layer singleton so LifecycleManager can drive it.
# ---------------------------------------------------------------------------

class _RAGLifecycleService(BaseLifecycleService):
    @property
    def name(self) -> str:
        return "rag_service"

    async def initialize(self) -> None:
        from app.dependencies.composition import get_rag_service
        await get_rag_service().initialize()

    async def close(self) -> None:
        from app.dependencies.composition import get_rag_service
        await get_rag_service().close()


class _NavigationLifecycleService(BaseLifecycleService):
    @property
    def name(self) -> str:
        return "navigation_service"

    async def initialize(self) -> None:
        from app.dependencies.composition import get_navigation_service
        await get_navigation_service().initialize()

    async def close(self) -> None:
        from app.dependencies.composition import get_navigation_service
        await get_navigation_service().close()


class _BrowserLifecycleService(BaseLifecycleService):
    @property
    def name(self) -> str:
        return "browser_service"

    async def initialize(self) -> None:
        from app.dependencies.composition import get_browser_service
        await get_browser_service().initialize()

    async def close(self) -> None:
        from app.dependencies.composition import get_browser_service
        await get_browser_service().close()


class _AgentLifecycleService(BaseLifecycleService):
    @property
    def name(self) -> str:
        return "agent_service"

    async def initialize(self) -> None:
        from app.dependencies.composition import get_agent_service
        await get_agent_service().initialize()

    async def close(self) -> None:
        from app.dependencies.composition import get_agent_service
        await get_agent_service().close()


class _OrchestratorLifecycleService(BaseLifecycleService):
    @property
    def name(self) -> str:
        return "orchestrator_service"

    async def initialize(self) -> None:
        from app.dependencies.composition import get_orchestrator_service
        await get_orchestrator_service().initialize()

    async def close(self) -> None:
        from app.dependencies.composition import get_orchestrator_service
        await get_orchestrator_service().close()


# ---------------------------------------------------------------------------
# Lifecycle manager factory
# Registration order drives startup sequence; shutdown runs in reverse.
# ---------------------------------------------------------------------------

def _build_lifecycle_manager() -> LifecycleManager:
    """Build and return a LifecycleManager with all AI subsystem services registered."""
    container = ApplicationContainer(settings=ApplicationSettings())
    manager = LifecycleManager(container=container)

    # Startup order: RAG → Navigation → Browser → Agent → Orchestrator
    # Shutdown order is automatically reversed by LifecycleManager.
    manager.register_service(_RAGLifecycleService())
    manager.register_service(_NavigationLifecycleService())
    manager.register_service(_BrowserLifecycleService())
    manager.register_service(_AgentLifecycleService())
    manager.register_service(_OrchestratorLifecycleService())

    return manager


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage AI subsystem startup and graceful shutdown around FastAPI's lifespan."""
    manager = _build_lifecycle_manager()
    await manager.initialize()
    try:
        yield
    finally:
        await manager.shutdown()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application with AI subsystem lifecycle.

    Returns:
        FastAPI: Fully configured application instance.
    """
    configure_logging(settings.logging.level.value)

    application = FastAPI(
        title=settings.application.app_name,
        version=settings.application.app_version,
        debug=settings.application.debug,
        lifespan=_lifespan,
    )

    application.include_router(
        api_router,
        prefix=settings.application.api_v1_prefix,
    )

    return application