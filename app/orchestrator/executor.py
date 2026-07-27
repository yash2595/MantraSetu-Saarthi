"""Orchestrator Executor module for MantraSetu AgentOS.

This module implements OrchestratorExecutor for executing an ExecutionPlan sequence,
enforcing dependency resolution, delegating target routing to BaseRouter, and dispatching
step execution strictly to injected BaseExecutionHandler implementations.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Mapping
from uuid import UUID

from app.orchestrator.base import (
    BaseExecutionHandler,
    BaseExecutor,
    BaseRouter,
    ExecutionError,
)
from app.orchestrator.models import (
    ExecutionContext,
    ExecutionMetadata,
    ExecutionPlan,
    ExecutionResult,
    ExecutionStatus,
    ExecutionStep,
    ExecutionTarget,
)


class OrchestratorExecutor(BaseExecutor):
    """Production workflow execution engine implementing BaseExecutor contract.

    Responsibility:
        Validates ExecutionPlan step dependency graphs, delegates target subsystem routing
        to BaseRouter, dispatches step execution to injected BaseExecutionHandler models,
        aggregates step outputs deterministically, and supports cooperative cancellation.
    """

    def __init__(
        self,
        router: BaseRouter,
        handlers: Mapping[ExecutionTarget, BaseExecutionHandler],
    ) -> None:
        """Initialize OrchestratorExecutor with router and handler mapping dependencies.

        Args:
            router: BaseRouter implementation for target resolution.
            handlers: Injected mapping of ExecutionTarget enums to BaseExecutionHandler instances.
        """
        self._router = router
        self._handlers: dict[ExecutionTarget, BaseExecutionHandler] = dict(handlers)
        self._cancelled_plans: set[UUID] = set()
        self._lock = asyncio.Lock()

    async def cancel(self, plan_id: UUID) -> None:
        """Register a cooperative cancellation request for an active plan execution.

        Args:
            plan_id: Unique plan identifier UUID to cancel.
        """
        async with self._lock:
            self._cancelled_plans.add(plan_id)

    async def execute(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute an ExecutionPlan sequence and return an immutable ExecutionResult.

        Args:
            plan: ExecutionPlan model specifying steps and parameters.

        Returns:
            ExecutionResult: Immutable final outcome result model.

        Raises:
            ExecutionError: If plan validation fails, dependencies fail, or a step execution errors.
        """
        self._validate_plan(plan)
        context = self._prepare_context(plan)
        return await self._execute_plan(plan, context)

    # ------------------------------------------------------------------
    # Private Execution Helpers
    # ------------------------------------------------------------------

    def _validate_plan(self, plan: ExecutionPlan) -> None:
        """Validate input ExecutionPlan integrity.

        Args:
            plan: ExecutionPlan model.

        Raises:
            ExecutionError: If plan is None, missing plan_id, or has no steps.
        """
        if not plan:
            raise ExecutionError("ExecutionPlan cannot be None.")

        if not plan.plan_id:
            raise ExecutionError("ExecutionPlan missing required plan_id.")

        if not plan.steps:
            raise ExecutionError("ExecutionPlan contains no steps to execute.")

    def _prepare_context(self, plan: ExecutionPlan) -> ExecutionContext:
        """Create an initial immutable ExecutionContext for a plan.

        Args:
            plan: ExecutionPlan model.

        Returns:
            ExecutionContext: Initial runtime context model.
        """
        return ExecutionContext(
            plan_id=plan.plan_id,
            shared_variables={},
        )

    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        initial_context: ExecutionContext,
    ) -> ExecutionResult:
        """Iterate through plan steps, enforce dependencies, and dispatch execution.

        Args:
            plan: ExecutionPlan model.
            initial_context: Initial ExecutionContext instance.

        Returns:
            ExecutionResult: Final result model.

        Raises:
            ExecutionError: If step dependency checks fail or step execution encounters errors.
        """
        start_time = time.perf_counter()
        context = initial_context
        completed_step_ids: set[UUID] = set()

        for step in plan.steps:
            if await self._is_cancelled(plan.plan_id):
                await self._clear_cancellation(plan.plan_id)
                execution_time = (time.perf_counter() - start_time) * 1000
                return self._finalize_result(
                    plan_id=plan.plan_id,
                    status=ExecutionStatus.CANCELLED,
                    outputs=context.shared_variables,
                    error=f"Execution cancelled for plan {plan.plan_id}.",
                    execution_time_ms=execution_time,
                )

            if not self._check_dependencies(step, completed_step_ids):
                execution_time = (time.perf_counter() - start_time) * 1000
                raise ExecutionError(
                    f"Step '{step.name}' ({step.step_id}) unmet dependencies: {step.dependencies}."
                )

            context = context.model_copy(
                update={"current_step_id": step.step_id}
            )

            try:
                out = await self._execute_step(step, context)
                completed_step_ids.add(step.step_id)

                merged_outputs = self._aggregate_outputs(
                    context.shared_variables, out
                )

                context = context.model_copy(
                    update={
                        "completed_step_ids": tuple(completed_step_ids),
                        "shared_variables": merged_outputs,
                    }
                )
            except ExecutionError:
                raise
            except Exception as e:
                execution_time = (time.perf_counter() - start_time) * 1000
                raise ExecutionError(
                    f"Execution failed at step '{step.name}' ({step.step_id}): {str(e)}"
                ) from e

        execution_time = (time.perf_counter() - start_time) * 1000
        return self._finalize_result(
            plan_id=plan.plan_id,
            status=ExecutionStatus.COMPLETED,
            outputs=context.shared_variables,
            error=None,
            execution_time_ms=execution_time,
        )

    async def _execute_step(
        self,
        step: ExecutionStep,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Route step and delegate execution to the injected BaseExecutionHandler.

        Args:
            step: ExecutionStep model to execute.
            context: Current ExecutionContext state.

        Returns:
            dict[str, Any]: Output parameters dictionary from handler.

        Raises:
            ExecutionError: If routing fails or no handler is registered for target.
        """
        target = await self._router.route(step)
        handler = self._handlers.get(target)

        if not handler:
            raise ExecutionError(
                f"No execution handler registered for target '{target}' (step '{step.name}')."
            )

        return await handler.execute(step, context)

    def _check_dependencies(
        self,
        step: ExecutionStep,
        completed_step_ids: set[UUID],
    ) -> bool:
        """Check if all prerequisite step dependencies have completed.

        Args:
            step: Target ExecutionStep model.
            completed_step_ids: Set of completed step UUIDs.

        Returns:
            bool: True if dependencies met, False otherwise.
        """
        if not step.dependencies:
            return True
        return all(dep_id in completed_step_ids for dep_id in step.dependencies)

    def _aggregate_outputs(
        self,
        existing_outputs: dict[str, Any],
        step_output: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministically aggregate step outputs without silent key corruption.

        Args:
            existing_outputs: Currently accumulated outputs dictionary.
            step_output: New step output dictionary to merge.

        Returns:
            dict[str, Any]: Merged output dictionary.
        """
        merged = dict(existing_outputs)
        if isinstance(step_output, dict):
            merged.update(step_output)
        return merged

    def _finalize_result(
        self,
        plan_id: UUID,
        status: ExecutionStatus,
        outputs: dict[str, Any],
        error: str | None,
        execution_time_ms: float,
    ) -> ExecutionResult:
        """Construct final immutable ExecutionResult instance.

        Args:
            plan_id: Plan identifier UUID.
            status: Final ExecutionStatus enum value.
            outputs: Merged outputs dictionary.
            error: Optional diagnostic error message string.
            execution_time_ms: Execution duration in milliseconds.

        Returns:
            ExecutionResult: Final result model.
        """
        return ExecutionResult(
            plan_id=plan_id,
            status=status,
            outputs=outputs,
            error=error,
            execution_time_ms=execution_time_ms,
            metadata=ExecutionMetadata(
                source="OrchestratorExecutor",
                tags=(status.value,),
            ),
        )

    async def _is_cancelled(self, plan_id: UUID) -> bool:
        """Check thread-safely if a plan cancellation has been requested.

        Args:
            plan_id: Plan identifier UUID.

        Returns:
            bool: True if cancelled, False otherwise.
        """
        async with self._lock:
            return plan_id in self._cancelled_plans

    async def _clear_cancellation(self, plan_id: UUID) -> None:
        """Clear a plan cancellation record after handling.

        Args:
            plan_id: Plan identifier UUID.
        """
        async with self._lock:
            self._cancelled_plans.discard(plan_id)
