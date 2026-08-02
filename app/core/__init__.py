"""Core application infrastructure subpackage for MantraSetu AgentOS."""

from app.core.app import create_app
from app.core.bootstrap import ApplicationBootstrap, BootstrapReport, bootstrap_application, shutdown_application
from app.core.config import get_settings, settings, Settings
from app.core.container import ApplicationContainer, Scope
from app.core.exceptions import ApplicationError, ConfigurationError, DependencyError
from app.core.lifecycle import BaseLifecycleService, LifecycleManager, LifecycleState
from app.core.logging import configure_logging
from app.core.registry import get_runtime_registry, reset_runtime_registry, RuntimeRegistry
from app.core.shutdown import GracefulShutdownManager
from app.core.validation import StartupValidationError, StartupValidator

__all__ = [
    "ApplicationBootstrap",
    "ApplicationContainer",
    "ApplicationError",
    "BaseLifecycleService",
    "BootstrapReport",
    "ConfigurationError",
    "DependencyError",
    "GracefulShutdownManager",
    "LifecycleManager",
    "LifecycleState",
    "RuntimeRegistry",
    "Scope",
    "Settings",
    "StartupValidationError",
    "StartupValidator",
    "bootstrap_application",
    "configure_logging",
    "create_app",
    "get_runtime_registry",
    "get_settings",
    "reset_runtime_registry",
    "settings",
    "shutdown_application",
]
