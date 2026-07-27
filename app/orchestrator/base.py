"""Abstract contracts and interfaces for the Orchestrator subsystem in MantraSetu AgentOS.

This module defines abstract base classes for planning, routing, execution handlers, workflow execution,
and orchestrator engine facades alongside domain exception hierarchies, enforcing Dependency Inversion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.orchestrator.models import (
    ExecutionContext,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStep,
    ExecutionTarget,
)


class OrchestratorError(Exception):
    """Base exception for all orchestrator subsystem errors."""

    pass


class PlanningError(OrchestratorError):
    """Raised when execution plan generation fails."""

    pass


class RoutingError(OrchestratorError):
    """Raised when step routing resolution fails."""

    pass


class ExecutionError(OrchestratorError):
    """Raised when plan or step execution fails."""

    pass


class StateError(OrchestratorError):
    """Raised when context or runtime state transition validation fails."""

    pass


class HealthCheckError(OrchestratorError):
    """Raised when an orchestrator component health probe fails."""

    pass


class BasePlanner(ABC):
    """Abstract interface defining the contract for workflow plan generation."""

    @abstractmethod
    async def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        """Generate an ExecutionPlan DAG/sequence from an ExecutionRequest.

        Args:
            request: ExecutionRequest model specifying high-level task goal.

        Returns:
            ExecutionPlan: Generated execution plan entity.
        """
        ...


class BaseRouter(ABC):
    """Abstract interface defining the contract for step destination routing."""

    @abstractmethod
    async def route(self, step: ExecutionStep) -> ExecutionTarget:
        """Determine target subsystem execution destination for a workflow step.

        Args:
            step: ExecutionStep model to route.

        Returns:
            ExecutionTarget: Target execution subsystem enum value.
        """
        ...


class BaseExecutionHandler(ABC):
    """Abstract interface for target-specific step execution handlers."""

    @abstractmethod
    async def execute(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a single workflow step and return output parameters.

        Args:
            step: ExecutionStep model to execute.
            context: Immutable ExecutionContext runtime state.

        Returns:
            dict[str, Any]: Output parameters dictionary.
        """
        ...


class BaseExecutor(ABC):
    """Abstract interface defining the contract for workflow execution engine."""

    @abstractmethod
    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute an ExecutionPlan sequence and return final result.

        Args:
            plan: ExecutionPlan model to execute.

        Returns:
            ExecutionResult: Final outcome result model.
        """
        ...

    @abstractmethod
    async def cancel(self, plan_id: UUID) -> None:
        """Cancel ongoing execution of a running plan.

        Args:
            plan_id: Unique plan identifier UUID to cancel.
        """
        ...


class BaseOrchestrator(ABC):
    """Abstract top-level interface defining the complete Orchestrator subsystem contract."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize orchestrator runtime resources and sub-components."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close orchestrator runtime and release resources."""
        ...

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Process an ExecutionRequest from planning through execution to result.

        Args:
            request: ExecutionRequest model payload.

        Returns:
            ExecutionResult: Outcome result model.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health across orchestrator sub-components.

        Returns:
            bool: True if healthy, False otherwise.
        """
        ...
