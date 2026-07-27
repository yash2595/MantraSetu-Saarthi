"""FastAPI application factory.

Creates and configures the FastAPI application instance.
"""

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance.
    """

    # Configure application logging
    configure_logging(settings.logging.level.value)

    # Create FastAPI application
    application = FastAPI(
        title=settings.application.app_name,
        version=settings.application.app_version,
        debug=settings.application.debug,
    )

    # Register API routes
    application.include_router(
        api_router,
        prefix=settings.application.api_v1_prefix,
    )

    return application