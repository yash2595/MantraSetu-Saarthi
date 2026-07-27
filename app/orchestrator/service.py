"""Orchestrator Subsystem Service Facade for MantraSetu AgentOS.

This module provides OrchestratorService as the primary public entry point for the Orchestrator subsystem,
coordinating workflow planning via BasePlanner, state tracking via OrchestratorStateManager, and plan execution
via BaseExecutor without executing domain actions directly.
"""

from __future__ import annotations

from uuid import UUID

from app.orchestrator.base import (
    BaseExecutor,
    BaseOrchestrator,
    BasePlanner,
    ExecutionError,
)
from app.orchestrator.models import (
    ExecutionContext,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionResult,
)
from app.orchestrator.state import OrchestratorStateManager


class OrchestratorService(BaseOrchestrator):
    """Public facade service implementing BaseOrchestrator contract.

    Responsibility:
        Coordinates end-to-end task execution workflow by validating requests, delegating planning
        to BasePlanner, persisting runtime context via OrchestratorStateManager, and executing plans
        via BaseExecutor. Guarantees state cleanup on both success and error conditions.
    """

    def __init__(
        self,
        planner: BasePlanner,
        executor: BaseExecutor,
        state_manager: OrchestratorStateManager,
    ) -> None:
        """Initialize OrchestratorService with injected planner, executor, and state manager.

        Args:
            planner: BasePlanner instance generating execution plans.
            executor: BaseExecutor instance executing workflow plans.
            state_manager: OrchestratorStateManager instance tracking runtime execution context.
        """
        self._planner = planner
        self._executor = executor
        self._state_manager = state_manager
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the orchestrator service has been initialized.

        Raises:
            ExecutionError: If service is uninitialized.
        """
        if not self._initialized:
            raise ExecutionError(
                "OrchestratorService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize the orchestrator service runtime state."""
        self._initialized = True

    async def close(self) -> None:
        """Close the orchestrator service and clear all active runtime state contexts."""
        await self._state_manager.clear()
        self._initialized = False

    async def health_check(self) -> bool:
        """Check operational health of the orchestrator service.

        Returns:
            bool: True if initialized, False otherwise.
        """
        return self._initialized

    async def cancel(self, plan_id: UUID) -> None:
        """Cancel ongoing execution of a running plan.

        Args:
            plan_id: Unique plan identifier UUID to cancel.

        Raises:
            ExecutionError: If service is uninitialized.
        """
        self._require_initialized()
        await self._executor.cancel(plan_id)

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Process an ExecutionRequest from plan generation to completion.

        Flow:
            1. Validate request
            2. Generate plan via planner
            3. Store runtime context via state_manager
            4. Execute plan via executor
            5. Always purge runtime context in finally block
            6. Return ExecutionResult

        Args:
            request: ExecutionRequest model payload specifying task goal.

        Returns:
            ExecutionResult: Final outcome result model.

        Raises:
            ExecutionError: If validation, planning, or step execution fails.
        """
        self._require_initialized()
        self._validate_request(request)

        plan = await self._planner.plan(request)
        context = self._create_context(plan)
        await self._state_manager.store(context)

        try:
            result = await self._executor.execute(plan)
            return result
        finally:
            await self._cleanup(plan.plan_id)

    # ------------------------------------------------------------------
    # Private Helper Methods
    # ------------------------------------------------------------------

    def _validate_request(self, request: ExecutionRequest) -> None:
        """Validate input ExecutionRequest parameters.

        Args:
            request: ExecutionRequest model.

        Raises:
            ExecutionError: If request is None or missing goal.
        """
        if not request:
            raise ExecutionError("ExecutionRequest cannot be None.")

        if not request.goal or not request.goal.strip():
            raise ExecutionError("ExecutionRequest goal cannot be empty or blank.")

    def _create_context(self, plan: ExecutionPlan) -> ExecutionContext:
        """Construct an initial ExecutionContext model for a generated plan.

        Args:
            plan: ExecutionPlan model.

        Returns:
            ExecutionContext: Initial runtime context model.
        """
        return ExecutionContext(
            plan_id=plan.plan_id,
            shared_variables={},
        )

    async def _cleanup(self, plan_id: UUID) -> None:
        """Purge stored runtime context for a finished or failed plan.

        Args:
            plan_id: Plan identifier UUID.
        """
        try:
            if await self._state_manager.contains(plan_id):
                await self._state_manager.remove(plan_id)
        except Exception:
            pass
