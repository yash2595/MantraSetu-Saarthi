"""Abstract contracts and interfaces for the Orchestrator subsystem in MantraSetu AgentOS.

This module defines abstract base classes for intent detectors, execution routers,
execution managers, and full orchestration pipelines alongside the domain exception hierarchy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import (
    DetectedIntent,
    ExecutionRoute,
    OrchestratorContext,
    OrchestratorResponse,
    UserRequest,
)


class OrchestratorError(Exception):
    """Base exception for all orchestrator subsystem errors."""

    pass


class IntentDetectionError(OrchestratorError):
    """Raised when user intent classification or detection fails."""

    pass


class RoutingError(OrchestratorError):
    """Raised when intent-to-service execution routing resolution fails."""

    pass


class ExecutionRoutingError(OrchestratorError):
    """Raised when downstream service execution via resolved route fails."""

    pass


class OrchestrationExecutionError(OrchestratorError):
    """Raised when the orchestration pipeline execution fails."""

    pass


class OrchestratorInitializationError(OrchestratorError):
    """Raised when an orchestrator subsystem component initialization fails."""

    pass


class OrchestratorStoreError(OrchestratorError):
    """Raised when orchestrator context storage operations fail."""

    pass


class BaseIntentDetector(ABC):
    """Abstract interface defining the contract for user intent classification providers."""

    @abstractmethod
    async def detect(
        self,
        request: UserRequest,
    ) -> DetectedIntent:
        """Analyze a UserRequest and classify the detected user intent.

        Args:
            request: Incoming UserRequest model to classify.

        Returns:
            DetectedIntent: Classified intent model with type, confidence, and entities.

        Raises:
            IntentDetectionError: If intent detection or classification fails.
        """
        ...


class BaseRouter(ABC):
    """Abstract interface defining the contract for intent-based service execution routers."""

    @abstractmethod
    async def route(
        self,
        intent: DetectedIntent,
        context: OrchestratorContext,
    ) -> ExecutionRoute:
        """Resolve the execution service route for a detected intent and orchestrator context.

        Args:
            intent: DetectedIntent model from intent classification.
            context: Active OrchestratorContext model snapshot.

        Returns:
            ExecutionRoute: Resolved execution service routing plan model.

        Raises:
            RoutingError: If intent route resolution fails.
        """
        ...


class BaseExecutionManager(ABC):
    """Abstract interface defining the contract for downstream service execution managers."""

    @abstractmethod
    async def execute(
        self,
        route: ExecutionRoute,
        context: OrchestratorContext,
    ) -> OrchestratorResponse:
        """Execute a resolved ExecutionRoute by coordinating downstream services.

        Args:
            route: ExecutionRoute model resolved from intent classification.
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestration response from downstream service execution.

        Raises:
            ExecutionRoutingError: If downstream service execution fails.
        """
        ...


class BaseOrchestrator(ABC):
    """Abstract interface defining the contract for the full orchestration pipeline."""

    @abstractmethod
    async def process(
        self,
        request: UserRequest,
    ) -> OrchestratorResponse:
        """Execute the complete orchestration pipeline for an incoming UserRequest.

        Args:
            request: Incoming UserRequest model to orchestrate.

        Returns:
            OrchestratorResponse: Final orchestration response model.

        Raises:
            OrchestrationExecutionError: If orchestration pipeline execution fails.
        """
        ...
