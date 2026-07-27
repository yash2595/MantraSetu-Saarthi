"""Navigation Planner Service orchestration layer for MantraSetu AgentOS.

This module implements NavigationPlannerService, coordinating goal-oriented browser navigation plan creation
requests with an injected BaseNavigationPlanner implementation without browser execution SDKs.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    BaseNavigationPlanner,
    NavigationInitializationError,
    NavigationPlanningError,
)
from app.navigation.models import NavigationContext, NavigationPlan


class NavigationPlannerService:
    """Service facade coordinating navigation plan generation for user goals.

    Responsibility:
        Validates goal prompts and NavigationContext models, delegates plan generation to an injected
        BaseNavigationPlanner provider, translates planning errors into domain exceptions, and manages lifecycle health.
    """

    def __init__(self, planner: BaseNavigationPlanner) -> None:
        """Initialize NavigationPlannerService with an injected BaseNavigationPlanner dependency.

        Args:
            planner: Injected BaseNavigationPlanner implementation.
        """
        self._planner = planner
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the planner service has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "NavigationPlannerService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize planner service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._planner, "initialize"):
            await self._planner.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close planner service and release provider resources."""
        if hasattr(self._planner, "close"):
            await self._planner.close()

        self._initialized = False

    async def create_plan(
        self,
        goal: str,
        context: NavigationContext,
    ) -> NavigationPlan:
        """Validate input goal and generate a multi-step NavigationPlan via injected planner.

        Args:
            goal: Target user goal description string.
            context: NavigationContext model containing current page/session state.

        Returns:
            NavigationPlan: Created multi-step navigation plan entity.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationPlanningError: If goal is blank or planning execution fails.
        """
        self._require_initialized()
        if not goal or not goal.strip():
            raise NavigationPlanningError("Goal parameter string cannot be empty or blank.")
        if not isinstance(context, NavigationContext):
            raise NavigationPlanningError("Invalid NavigationContext instance provided.")

        try:
            return await self._planner.create_plan(goal, context)
        except NavigationPlanningError:
            raise
        except Exception as e:
            raise NavigationPlanningError(f"Navigation plan generation failed for goal '{goal}': {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the planner service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="navigation_planner_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="NavigationPlannerService uninitialized.",
            )

        planner_healthy = True
        if hasattr(self._planner, "health_check"):
            res = await self._planner.health_check()
            if isinstance(res, ComponentHealth):
                planner_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                planner_healthy = res

        return ComponentHealth(
            component_name="navigation_planner_service",
            status=SystemHealthStatus.HEALTHY if planner_healthy else SystemHealthStatus.UNHEALTHY,
            message="NavigationPlannerService operational."
            if planner_healthy
            else "NavigationPlannerService backend degraded.",
        )
