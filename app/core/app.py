"""FastAPI application factory with AI subsystem lifecycle integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.rest import rest_router
from app.api.websocket import ws_router
from app.core.bootstrap import bootstrap_application, shutdown_application
from app.core.config import settings
from app.core.logging import configure_logging


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup, runtime bootstrap, and graceful shutdown around FastAPI's lifespan."""
    bootstrap_application(app)
    try:
        yield
    finally:
        await shutdown_application()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with Module 5 application bootstrap.

    Returns:
        FastAPI: Fully configured application instance.
    """
    configure_logging(settings.log_level)

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=_lifespan,
    )

    # Register API v1, REST, and WebSocket routers
    from app.api.v1.router import api_router
    application.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(
        rest_router,
        prefix=settings.api_v1_prefix,
    )
    application.include_router(
        ws_router,
    )

    return application