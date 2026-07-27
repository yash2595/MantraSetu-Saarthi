"""Browser automation domain subsystem for MantraSetu AgentOS."""

from app.browser.base import (
    ActionExecutionError,
    BaseBrowserEngine,
    BaseBrowserExecutor,
    BaseBrowserSession,
    BatchExecutionError,
    BrowserError,
    BrowserExecutionError,
    BrowserRuntimeHandle,
    BrowserSessionError,
    SessionNotFoundError,
)
from app.browser.controller import BrowserController
from app.browser.executor import BrowserExecutor
from app.browser.models import (
    BaseBrowserModel,
    BrowserAction,
    BrowserActionType,
    BrowserBatch,
    BrowserExecutionStatus,
    BrowserResult,
    BrowserSession,
    BrowserSessionStatus,
    ElementReference,
    Metadata,
)
from app.browser.registry import (
    BrowserRegistry,
    BrowserRegistryError,
    ProviderAlreadyRegisteredError,
    ProviderNotFoundError,
)
from app.browser.service import BrowserService
from app.browser.session import BrowserSessionManager

__all__ = [
    "BaseBrowserModel",
    "BrowserActionType",
    "BrowserExecutionStatus",
    "BrowserSessionStatus",
    "ElementReference",
    "BrowserAction",
    "BrowserResult",
    "BrowserSession",
    "BrowserBatch",
    "Metadata",
    "BrowserRuntimeHandle",
    "BaseBrowserSession",
    "BaseBrowserExecutor",
    "BaseBrowserEngine",
    "BrowserSessionManager",
    "BrowserExecutor",
    "BrowserController",
    "BrowserRegistry",
    "BrowserRegistryError",
    "ProviderAlreadyRegisteredError",
    "ProviderNotFoundError",
    "BrowserService",
    "BrowserError",
    "BrowserSessionError",
    "SessionNotFoundError",
    "BrowserExecutionError",
    "ActionExecutionError",
    "BatchExecutionError",
]
