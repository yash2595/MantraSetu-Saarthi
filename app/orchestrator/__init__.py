"""Orchestrator subsystem for MantraSetu AgentOS."""

from app.orchestrator.base import (
    BaseExecutionManager,
    BaseIntentDetector,
    BaseOrchestrator,
    BaseRouter,
    ExecutionRoutingError,
    IntentDetectionError,
    OrchestrationExecutionError,
    OrchestratorError,
    OrchestratorInitializationError,
    OrchestratorStoreError,
    RoutingError,
)
from app.orchestrator.executor import ExecutionManager
from app.orchestrator.intent import IntentDetectionService
from app.orchestrator.models import (
    BaseOrchestratorModel,
    DetectedIntent,
    ExecutionRoute,
    IntentType,
    OrchestratorContext,
    OrchestratorResponse,
    UserRequest,
)
from app.orchestrator.router import RouterService
from app.orchestrator.service import OrchestratorService
from app.orchestrator.store import OrchestratorStore

__all__ = [
    # Models
    "BaseOrchestratorModel",
    "IntentType",
    "UserRequest",
    "DetectedIntent",
    "ExecutionRoute",
    "OrchestratorContext",
    "OrchestratorResponse",
    # Abstract contracts
    "BaseIntentDetector",
    "BaseRouter",
    "BaseExecutionManager",
    "BaseOrchestrator",
    # Services
    "IntentDetectionService",
    "RouterService",
    "ExecutionManager",
    "OrchestratorStore",
    "OrchestratorService",
    # Exceptions
    "OrchestratorError",
    "IntentDetectionError",
    "RoutingError",
    "ExecutionRoutingError",
    "OrchestrationExecutionError",
    "OrchestratorInitializationError",
    "OrchestratorStoreError",
]
