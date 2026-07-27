"""Orchestrator Planner module for MantraSetu AgentOS.

This module implements OrchestratorPlanner for deterministically decomposing an ExecutionRequest into
an ordered, immutable tuple of ExecutionStep instances wrapped inside an ExecutionPlan.
"""

from __future__ import annotations

from uuid import uuid4

from app.orchestrator.base import BasePlanner, PlanningError
from app.orchestrator.models import (
    ActionType,
    ExecutionMetadata,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionStep,
)


class OrchestratorPlanner(BasePlanner):
    """Deterministic workflow planner implementing BasePlanner contract.

    Responsibility:
        Validates ExecutionRequest parameters and generates an ordered, immutable ExecutionPlan
        containing configured ExecutionStep objects. Contains no execution logic, routing state, or side effects.
    """

    async def plan(self, request: ExecutionRequest) -> ExecutionPlan:
        """Decompose an ExecutionRequest into a validated immutable ExecutionPlan.

        Args:
            request: ExecutionRequest model specifying goal and parameters.

        Returns:
            ExecutionPlan: Generated execution plan entity.

        Raises:
            PlanningError: If request validation fails or plan creation encounters invalid state.
        """
        self._validate_request(request)
        steps = self._build_steps(request)
        return self._create_plan(request, steps)

    def _validate_request(self, request: ExecutionRequest) -> None:
        """Validate input ExecutionRequest parameters and goal integrity.

        Args:
            request: ExecutionRequest payload model.

        Raises:
            PlanningError: If goal is empty, whitespace, or parameters are invalid.
        """
        if not request:
            raise PlanningError("ExecutionRequest cannot be None.")

        if not request.goal or not request.goal.strip():
            raise PlanningError("ExecutionRequest goal cannot be empty or blank.")

        if not isinstance(request.parameters, dict):
            raise PlanningError("ExecutionRequest parameters must be a dictionary.")

    def _build_steps(
        self,
        request: ExecutionRequest,
    ) -> tuple[ExecutionStep, ...]:
        """Build an ordered tuple of ExecutionStep models for a request.

        Args:
            request: Validated ExecutionRequest model.

        Returns:
            tuple[ExecutionStep, ...]: Immutable tuple of configured ExecutionStep instances.
        """
        goal_lower = request.goal.lower()

        # Step 1: AI reasoning/intent analysis step
        step1_id = uuid4()
        step1 = ExecutionStep(
            step_id=step1_id,
            action_type=ActionType.AI,
            name="Analyze Intent and Plan Action",
            description=f"Analyze goal: '{request.goal}'",
            parameters={"goal": request.goal, **request.parameters},
            timeout_ms=15000,
            max_retries=2,
            metadata=ExecutionMetadata(source="planner", tags=("ai_reasoning",)),
        )

        # Step 2: Main action step based on goal keywords
        step2_id = uuid4()
        if "navigate" in goal_lower or "url" in goal_lower:
            action_type = ActionType.NAVIGATION
            step_name = "Execute Navigation Action"
        elif "click" in goal_lower or "browser" in goal_lower:
            action_type = ActionType.BROWSER
            step_name = "Execute Browser Action"
        elif "tool" in goal_lower or "search" in goal_lower:
            action_type = ActionType.TOOL
            step_name = "Execute Tool Invocation"
        else:
            action_type = ActionType.API
            step_name = "Execute API Command"

        step2 = ExecutionStep(
            step_id=step2_id,
            action_type=action_type,
            name=step_name,
            description=f"Execute primary action for goal: '{request.goal}'",
            parameters={"goal": request.goal, **request.parameters},
            dependencies=(step1_id,),
            timeout_ms=30000,
            max_retries=3,
            metadata=ExecutionMetadata(source="planner", tags=("primary_action",)),
        )

        return (step1, step2)

    def _create_plan(
        self,
        request: ExecutionRequest,
        steps: tuple[ExecutionStep, ...],
    ) -> ExecutionPlan:
        """Construct the final immutable ExecutionPlan model.

        Args:
            request: Associated ExecutionRequest instance.
            steps: Tuple of ordered ExecutionStep models.

        Returns:
            ExecutionPlan: Final plan model.
        """
        return ExecutionPlan(
            request_id=request.request_id,
            steps=steps,
            metadata=ExecutionMetadata(
                source="OrchestratorPlanner",
                tags=("deterministic_plan",),
            ),
        )
