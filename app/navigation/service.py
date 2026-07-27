"""Navigation Intelligence Application Service facade for MantraSetu AgentOS.

This module implements NavigationService as the main application facade exposing
website analysis, navigation planning, structure graph indexing, context persistence, and backtracking.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.analyzer import NavigationAnalyzerService
from app.navigation.backtracking import BacktrackingService
from app.navigation.base import (
    NavigationError,
    NavigationInitializationError,
)
from app.navigation.graph import NavigationGraph
from app.navigation.models import (
    NavigationContext,
    NavigationPlan,
    WebsiteNode,
)
from app.navigation.planner import NavigationPlannerService
from app.navigation.store import NavigationStore


class NavigationService:
    """Application facade service coordinating Navigation Intelligence subsystem components.

    Responsibility:
        Orchestrates website structure analysis, goal plan generation, site map graph indexing,
        navigation context persistence, and state backtracking without Playwright or browser execution SDKs.
    """

    def __init__(
        self,
        planner_service: NavigationPlannerService,
        analyzer_service: NavigationAnalyzerService,
        graph: NavigationGraph,
        backtracking_service: BacktrackingService,
        store: NavigationStore,
    ) -> None:
        """Initialize NavigationService with strictly injected dependencies.

        Args:
            planner_service: Injected NavigationPlannerService instance.
            analyzer_service: Injected NavigationAnalyzerService instance.
            graph: Injected NavigationGraph instance.
            backtracking_service: Injected BacktrackingService instance.
            store: Injected NavigationStore instance.
        """
        self._planner_service = planner_service
        self._analyzer_service = analyzer_service
        self._graph = graph
        self._backtracking_service = backtracking_service
        self._store = store
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the navigation service has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "NavigationService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize navigation service and underlying subsystem components. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._analyzer_service, "initialize"):
            await self._analyzer_service.initialize()
        if hasattr(self._planner_service, "initialize"):
            await self._planner_service.initialize()
        if hasattr(self._graph, "initialize"):
            await self._graph.initialize()
        if hasattr(self._backtracking_service, "initialize"):
            await self._backtracking_service.initialize()
        if hasattr(self._store, "initialize"):
            await self._store.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close navigation service and release all subsystem resources."""
        if hasattr(self._store, "close"):
            await self._store.close()
        if hasattr(self._backtracking_service, "close"):
            await self._backtracking_service.close()
        if hasattr(self._graph, "close"):
            await self._graph.close()
        if hasattr(self._planner_service, "close"):
            await self._planner_service.close()
        if hasattr(self._analyzer_service, "close"):
            await self._analyzer_service.close()

        self._initialized = False

    async def analyze_website(
        self,
        url: str,
    ) -> tuple[WebsiteNode, ...]:
        """Analyze a web page URL, discover WebsiteNode entities, and index them into graph and store.

        Args:
            url: Page or website URL string to analyze.

        Returns:
            tuple[WebsiteNode, ...]: Immutable tuple of discovered WebsiteNode entities.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationError: If analysis or node indexing fails.
        """
        self._require_initialized()
        try:
            nodes = await self._analyzer_service.analyze(url)
            for node in nodes:
                await self._graph.add_node(node)
                await self._store.save_node(node)
            return nodes
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to analyze website URL '{url}': {str(e)}") from e

    async def create_plan(
        self,
        goal: str,
        context: NavigationContext,
    ) -> NavigationPlan:
        """Generate a multi-step NavigationPlan for a goal delegating to NavigationPlannerService.

        Args:
            goal: Target user goal description string.
            context: NavigationContext model snapshot.

        Returns:
            NavigationPlan: Created navigation plan entity.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationError: If planning execution or plan persistence fails.
        """
        self._require_initialized()
        try:
            plan = await self._planner_service.create_plan(goal, context)
            await self._store.save_plan(plan)
            return plan
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to create navigation plan for goal '{goal}': {str(e)}") from e

    async def execute_backtrack(self) -> NavigationContext:
        """Backtrack to previous valid NavigationContext snapshot via BacktrackingService.

        Returns:
            NavigationContext: Restored previous valid navigation context model.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationError: If no previous context exists or backtracking fails.
        """
        self._require_initialized()
        try:
            restored_ctx = await self._backtracking_service.backtrack()
            if restored_ctx.session_id is not None:
                await self._store.save_context(restored_ctx)
            return restored_ctx
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Navigation backtrack execution failed: {str(e)}") from e

    async def save_context(
        self,
        context: NavigationContext,
    ) -> None:
        """Save a NavigationContext snapshot into history stack and store.

        Args:
            context: NavigationContext model snapshot.

        Raises:
            NavigationInitializationError: If service is uninitialized.
            NavigationError: If context persistence fails.
        """
        self._require_initialized()
        try:
            await self._backtracking_service.push_state(context)
            if context.session_id is not None:
                await self._store.save_context(context)
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to save navigation context: {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check aggregated operational health across all 5 Navigation Intelligence components.

        Returns:
            ComponentHealth: Aggregated component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="navigation_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="NavigationService uninitialized.",
            )

        analyzer_health = await self._analyzer_service.health_check()
        planner_health = await self._planner_service.health_check()
        graph_health = await self._graph.health_check()
        backtracking_health = await self._backtracking_service.health_check()
        store_health = await self._store.health_check()

        is_healthy = (
            isinstance(analyzer_health, ComponentHealth)
            and analyzer_health.status == SystemHealthStatus.HEALTHY
            and isinstance(planner_health, ComponentHealth)
            and planner_health.status == SystemHealthStatus.HEALTHY
            and isinstance(graph_health, ComponentHealth)
            and graph_health.status == SystemHealthStatus.HEALTHY
            and isinstance(backtracking_health, ComponentHealth)
            and backtracking_health.status == SystemHealthStatus.HEALTHY
            and isinstance(store_health, ComponentHealth)
            and store_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="navigation_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="NavigationService operational."
            if is_healthy
            else "NavigationService subsystem component degraded.",
        )
