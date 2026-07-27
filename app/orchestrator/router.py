"""Orchestrator Router module for MantraSetu AgentOS.

This module implements OrchestratorRouter for deterministically routing an ExecutionStep
to its corresponding target subsystem enum without performing step execution or keyword inference.
"""

from __future__ import annotations

from app.orchestrator.base import BaseRouter, RoutingError
from app.orchestrator.models import (
    ActionType,
    ExecutionStep,
    ExecutionTarget,
)


class OrchestratorRouter(BaseRouter):
    """Deterministic step router implementing BaseRouter contract.

    Responsibility:
        Maps ExecutionStep models to their target ExecutionTarget subsystem enums
        using explicit ActionType dispatch rules without performing step execution or AI reasoning.
    """

    async def route(self, step: ExecutionStep) -> ExecutionTarget:
        """Resolve the target ExecutionTarget subsystem enum for an ExecutionStep.

        Args:
            step: ExecutionStep model to route.

        Returns:
            ExecutionTarget: Target subsystem enum value.

        Raises:
            RoutingError: If step validation fails or action type is unsupported.
        """
        self._validate_step(step)
        return self._resolve_target(step.action_type)

    def _validate_step(self, step: ExecutionStep) -> None:
        """Validate input ExecutionStep integrity.

        Args:
            step: ExecutionStep instance to validate.

        Raises:
            RoutingError: If step is None or missing required identifiers.
        """
        if not step:
            raise RoutingError("ExecutionStep cannot be None.")

        if not step.step_id:
            raise RoutingError("ExecutionStep missing required step_id.")

        if not step.action_type:
            raise RoutingError("ExecutionStep missing required action_type.")

    def _resolve_target(self, action_type: ActionType) -> ExecutionTarget:
        """Deterministically map an ActionType enum to its corresponding ExecutionTarget enum.

        Args:
            action_type: ActionType enum value.

        Returns:
            ExecutionTarget: Target execution subsystem enum value.

        Raises:
            RoutingError: If action_type cannot be resolved to a valid execution target.
        """
        target_map: dict[ActionType, ExecutionTarget] = {
            ActionType.AI: ExecutionTarget.AI,
            ActionType.NAVIGATION: ExecutionTarget.NAVIGATION,
            ActionType.BROWSER: ExecutionTarget.BROWSER,
            ActionType.TOOL: ExecutionTarget.TOOL,
            ActionType.API: ExecutionTarget.SYSTEM,
            ActionType.WAIT: ExecutionTarget.SYSTEM,
            ActionType.USER_INPUT: ExecutionTarget.SYSTEM,
        }

        target = target_map.get(action_type)
        if not target:
            raise RoutingError(
                f"Unsupported action_type '{action_type}' for subsystem routing."
            )

        return target
