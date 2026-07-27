"""Navigation Planner domain service for MantraSetu AgentOS.

This module provides the NavigationPlanner domain service, RouteStrategy interface,
and SimpleRouteStrategy for constructing navigation plans without executing browser actions
or mutating graph and store states.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.navigation.analyzer import NavigationAnalysis, NavigationAnalyzer
from app.navigation.graph import NavigationGraph
from app.navigation.models import (
    NavigationAction,
    NavigationPlan,
    NavigationStatus,
)
from app.navigation.store import BaseNavigationStore


class NavigationPlanningError(Exception):
    """Base domain exception raised when navigation planning fails."""

    pass


class NodeNotFoundError(NavigationPlanningError):
    """Raised when a source or target node is missing from the navigation graph."""

    pass


class NoRouteFoundError(NavigationPlanningError):
    """Raised when no valid path exists between source and target nodes."""

    pass


class NavigationRecoveryRequiredError(NavigationPlanningError):
    """Raised when navigation history indicates a loop or state requiring recovery/backtracking."""

    pass


class RouteStrategy(ABC):
    """Abstract strategy contract for resolving navigation routes between graph nodes."""

    @abstractmethod
    def find_route(
        self,
        graph: NavigationGraph,
        source_node_id: UUID,
        target_node_id: UUID,
    ) -> tuple[NavigationAction, ...]:
        """Find a sequence of navigation actions to transition from source to target node.

        Args:
            graph: NavigationGraph instance holding application topology.
            source_node_id: Identifier of the source node.
            target_node_id: Identifier of the target destination node.

        Returns:
            tuple[NavigationAction, ...]: Sequence of planned actions, or empty tuple if no route found.
        """
        ...


class SimpleRouteStrategy(RouteStrategy):
    """Simple routing strategy that evaluates direct edges and two-hop neighbor transitions."""

    def find_route(
        self,
        graph: NavigationGraph,
        source_node_id: UUID,
        target_node_id: UUID,
    ) -> tuple[NavigationAction, ...]:
        """Find a route via direct edge or two-hop neighbor transitions.

        Args:
            graph: NavigationGraph instance holding application topology.
            source_node_id: Identifier of the source node.
            target_node_id: Identifier of the target destination node.

        Returns:
            tuple[NavigationAction, ...]: Action tuple forming the route.
        """
        direct_edge = graph.get_edge_between(source_node_id, target_node_id)
        if direct_edge:
            return (direct_edge.action,)

        for neighbor in graph.outgoing_neighbors(source_node_id):
            hop1 = graph.get_edge_between(source_node_id, neighbor.node_id)
            hop2 = graph.get_edge_between(neighbor.node_id, target_node_id)
            if hop1 and hop2:
                return (hop1.action, hop2.action)

        return ()


class NavigationPlanner:
    """Domain service responsible for constructing navigation plans.

    Responsibility:
        Orchestrates session validation, strategy-based route resolution, and immutable NavigationPlan
        construction without mutating graph/store state or executing browser automation.
    """

    def __init__(
        self,
        graph: NavigationGraph,
        store: BaseNavigationStore,
        analyzer: NavigationAnalyzer,
        route_strategy: RouteStrategy | None = None,
    ) -> None:
        """Initialize NavigationPlanner with graph, store, analyzer, and route strategy dependencies.

        Args:
            graph: NavigationGraph instance holding application topology.
            store: BaseNavigationStore instance for reading session states.
            analyzer: NavigationAnalyzer instance for read-only session analysis.
            route_strategy: Optional RouteStrategy instance. Defaults to SimpleRouteStrategy.
        """
        self._graph = graph
        self._store = store
        self._analyzer = analyzer
        self._route_strategy = route_strategy or SimpleRouteStrategy()

    async def initialize(self) -> None:
        """Initialize planner resources (no-op)."""
        pass

    async def close(self) -> None:
        """Close planner resources (no-op)."""
        pass

    async def can_plan(self, session_id: UUID, target_node_id: UUID) -> bool:
        """Determine whether a navigation plan can be constructed for a session and target.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Intended target destination node identifier.

        Returns:
            bool: True if planning is possible, False otherwise.
        """
        try:
            analysis = await self._validate_analysis(session_id, target_node_id)
            if not analysis.current_node:
                return False
            if analysis.current_node.node_id == target_node_id:
                return True
            actions = self._route_strategy.find_route(
                self._graph, analysis.current_node.node_id, target_node_id
            )
            return len(actions) > 0
        except NavigationPlanningError:
            return False

    async def requires_backtracking(self, session_id: UUID) -> bool:
        """Evaluate whether the session history indicates a loop or repeated state requiring backtracking.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            bool: True if history suggests backtracking is required, False otherwise.
        """
        history = await self._store.get_history(session_id)
        return await self._analyzer.should_backtrack(history)

    async def create_plan(
        self,
        session_id: UUID,
        target_node_id: UUID,
    ) -> NavigationPlan:
        """Construct an immutable NavigationPlan for navigating to the target node.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Intended destination target node identifier.

        Returns:
            NavigationPlan: Constructed navigation plan manifest.

        Raises:
            NodeNotFoundError: If source or target nodes do not exist in the graph.
            NavigationRecoveryRequiredError: If navigation history requires recovery or backtracking.
            NoRouteFoundError: If no valid route can be determined.
        """
        analysis = await self._validate_analysis(session_id, target_node_id)

        source_node = analysis.current_node
        if not source_node:
            raise NodeNotFoundError(
                f"Session {session_id} active node could not be resolved from graph."
            )

        if source_node.node_id == target_node_id:
            return self._create_completed_plan(source_node.node_id, target_node_id)

        if await self.requires_backtracking(session_id):
            raise NavigationRecoveryRequiredError(
                f"Session {session_id} history contains loops or repeated states requiring recovery."
            )

        actions = self._route_strategy.find_route(
            self._graph, source_node.node_id, target_node_id
        )
        if not actions:
            raise NoRouteFoundError(
                f"No route found from node {source_node.node_id} to target node {target_node_id}."
            )

        return self._build_plan(
            source_node_id=source_node.node_id,
            target_node_id=target_node_id,
            actions=list(actions),
            status=NavigationStatus.PENDING,
        )

    async def _validate_analysis(
        self,
        session_id: UUID,
        target_node_id: UUID,
    ) -> NavigationAnalysis:
        """Internal helper to perform read-only session analysis and check target node existence.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Target node identifier.

        Returns:
            NavigationAnalysis: Analyzed session model.

        Raises:
            NodeNotFoundError: If target node does not exist in graph.
        """
        if not self._graph.has_node(target_node_id):
            raise NodeNotFoundError(f"Target node {target_node_id} does not exist in graph.")

        analysis = await self._analyzer.analyze_session(session_id, target_node_id)
        return analysis

    def _build_plan(
        self,
        source_node_id: UUID,
        target_node_id: UUID,
        actions: list[NavigationAction],
        status: NavigationStatus,
    ) -> NavigationPlan:
        """Internal helper to construct a NavigationPlan instance.

        Args:
            source_node_id: Source node identifier.
            target_node_id: Target node identifier.
            actions: List of planned navigation actions.
            status: Initial plan status.

        Returns:
            NavigationPlan: Constructed plan model.
        """
        return NavigationPlan(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            actions=actions,
            status=status,
            estimated_cost=float(len(actions)),
            estimated_steps=len(actions),
        )

    def _create_completed_plan(
        self,
        source_node_id: UUID,
        target_node_id: UUID,
    ) -> NavigationPlan:
        """Internal helper to construct an already-completed navigation plan when at target.

        Args:
            source_node_id: Source node identifier.
            target_node_id: Target node identifier.

        Returns:
            NavigationPlan: Completed plan model with status=COMPLETED and empty actions.
        """
        return self._build_plan(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            actions=[],
            status=NavigationStatus.COMPLETED,
        )
