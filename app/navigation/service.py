"""Navigation Service orchestrator module for MantraSetu AgentOS.

This module provides the NavigationService orchestrator, coordinating the NavigationGraph,
BaseNavigationStore, NavigationAnalyzer, NavigationPlanner, and NavigationBacktracker to manage
session navigation lifecycles, state persistence, and exception handling without embedding planning
or browser execution logic.
"""

from __future__ import annotations

import time
from uuid import UUID

from app.navigation.analyzer import NavigationAnalyzer
from app.navigation.backtracking import BacktrackingError, NavigationBacktracker
from app.navigation.base import BaseNavigationEngine
from app.navigation.graph import NavigationGraph
from app.navigation.models import (
    NavigationAction,
    NavigationHistory,
    NavigationHistoryEntry,
    NavigationPlan,
    NavigationResult,
    NavigationState,
    NavigationStatus,
)
from app.navigation.planner import NavigationPlanner, NavigationPlanningError
from app.navigation.store import BaseNavigationStore


class NavigationService(BaseNavigationEngine):
    """High-level orchestration service for session navigation lifecycles.

    Responsibility:
        Coordinates graph, store, analyzer, planner, and backtracker components.
        Owns all persistence operations and exception translation into clean NavigationResult outputs.
    """

    def __init__(
        self,
        graph: NavigationGraph,
        store: BaseNavigationStore,
        analyzer: NavigationAnalyzer,
        planner: NavigationPlanner,
        backtracker: NavigationBacktracker,
    ) -> None:
        """Initialize NavigationService with domain component dependencies.

        Args:
            graph: NavigationGraph instance.
            store: BaseNavigationStore instance.
            analyzer: NavigationAnalyzer instance.
            planner: NavigationPlanner instance.
            backtracker: NavigationBacktracker instance.
        """
        self._graph = graph
        self._store = store
        self._analyzer = analyzer
        self._planner = planner
        self._backtracker = backtracker

    async def initialize(self) -> None:
        """Initialize all underlying store, analyzer, planner, and backtracker resources."""
        await self._store.initialize()
        await self._analyzer.initialize()
        await self._planner.initialize()
        await self._backtracker.initialize()

    async def close(self) -> None:
        """Close and release all underlying component resources."""
        await self._backtracker.close()
        await self._planner.close()
        await self._analyzer.close()
        await self._store.close()

    async def get_state(self, session_id: UUID) -> NavigationState:
        """Retrieve active navigation state for a session.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            NavigationState: Active session state.
        """
        state = await self._store.get_state(session_id)
        if not state:
            state = NavigationState(session_id=session_id)
            await self._store.save_state(state)
        return state

    async def update_state(self, state: NavigationState) -> None:
        """Persist updated navigation state for a session.

        Args:
            state: NavigationState instance to store.
        """
        await self._store.save_state(state)

    async def get_history(self, session_id: UUID) -> NavigationHistory:
        """Retrieve navigation history for a session.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            NavigationHistory: Session history log.
        """
        history = await self._store.get_history(session_id)
        if not history:
            history = NavigationHistory(session_id=session_id)
            await self._store.save_history(history)
        return history

    async def can_navigate(
        self,
        source_node_id: UUID,
        target_node_id: UUID,
    ) -> bool:
        """Determine whether navigation transition is possible between source and target nodes.

        Args:
            source_node_id: Source node identifier.
            target_node_id: Target node identifier.

        Returns:
            bool: True if a direct edge or two-hop transition exists, False otherwise.
        """
        if not self._graph.has_node(source_node_id) or not self._graph.has_node(target_node_id):
            return False

        if self._graph.get_edge_between(source_node_id, target_node_id) is not None:
            return True

        return any(
            self._graph.get_edge_between(neighbor.node_id, target_node_id) is not None
            for neighbor in self._graph.outgoing_neighbors(source_node_id)
        )

    async def plan_navigation(
        self,
        session_id: UUID,
        target_node_id: UUID,
    ) -> NavigationPlan:
        """Delegate navigation plan creation for a session and target node.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Target destination node identifier.

        Returns:
            NavigationPlan: Constructed navigation plan.
        """
        return await self._planner.create_plan(session_id, target_node_id)

    async def reset(self, session_id: UUID) -> None:
        """Reset and clear session state, history, and plans.

        Args:
            session_id: Unique navigation session identifier.
        """
        await self.reset_session(session_id)

    async def reset_session(self, session_id: UUID) -> None:
        """Purge all navigation artifacts for a session.

        Args:
            session_id: Unique navigation session identifier.
        """
        await self._store.clear_session(session_id)

    async def health_check(self) -> bool:
        """Check store health status for navigation operations.

        Returns:
            bool: True if the navigation store is healthy and operational, False otherwise.
        """
        return await self._store.health_check()

    async def navigate(
        self,
        session_id: UUID,
        target_node_id: UUID,
    ) -> NavigationResult:
        """Orchestrate navigation toward a target node for a session.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Intended destination target node identifier.

        Returns:
            NavigationResult: Summary of navigation attempt.
        """
        start_time = time.perf_counter()

        try:
            state = await self.get_state(session_id)
            analysis = await self._analyzer.analyze_session(session_id, target_node_id)

            if analysis.loop.loop_detected or await self._backtracker.recovery_required(session_id):
                return await self._handle_recovery(session_id, state, start_time)

            plan = await self.plan_navigation(session_id, target_node_id)
            await self._store.save_plan(plan, session_id)

            if plan.status == NavigationStatus.COMPLETED:
                return self._build_result(
                    success=True,
                    status=NavigationStatus.COMPLETED,
                    final_node_id=target_node_id,
                    executed_actions=plan.actions,
                    steps_completed=0,
                    steps_total=0,
                    start_time=start_time,
                )

            first_action = plan.actions[0] if plan.actions else None
            updated_state = NavigationState(
                session_id=session_id,
                current_node_id=state.current_node_id,
                current_route=state.current_route,
                current_action=first_action,
                current_plan_id=plan.plan_id,
                status=NavigationStatus.IN_PROGRESS,
                visited_nodes=state.visited_nodes,
            )
            await self._store.save_state(updated_state)

            if state.current_node_id:
                await self._append_history_entry(
                    session_id=session_id,
                    node_id=state.current_node_id,
                    action=first_action,
                    route=state.current_route,
                )

            return self._build_result(
                success=True,
                status=NavigationStatus.IN_PROGRESS,
                final_node_id=state.current_node_id,
                executed_actions=plan.actions,
                steps_completed=0,
                steps_total=len(plan.actions),
                start_time=start_time,
            )

        except (NavigationPlanningError, BacktrackingError) as e:
            return self._build_result(
                success=False,
                status=NavigationStatus.FAILED,
                final_node_id=None,
                executed_actions=[],
                steps_completed=0,
                steps_total=0,
                start_time=start_time,
                error=str(e),
            )
        except Exception as e:
            return self._build_result(
                success=False,
                status=NavigationStatus.FAILED,
                final_node_id=None,
                executed_actions=[],
                steps_completed=0,
                steps_total=0,
                start_time=start_time,
                error=f"Unexpected navigation error: {str(e)}",
            )

    async def _handle_recovery(
        self,
        session_id: UUID,
        state: NavigationState,
        start_time: float,
    ) -> NavigationResult:
        """Internal helper to process session recovery via backtracker.

        Args:
            session_id: Session identifier.
            state: Active NavigationState instance.
            start_time: Navigation start time benchmark.

        Returns:
            NavigationResult: Recovery outcome result.
        """
        recovery_plan = await self._backtracker.create_recovery_plan(session_id)
        await self._store.save_plan(recovery_plan, session_id)

        first_action = recovery_plan.actions[0] if recovery_plan.actions else None
        updated_state = NavigationState(
            session_id=session_id,
            current_node_id=recovery_plan.recovery_node_id,
            current_route=state.current_route,
            current_action=first_action,
            current_plan_id=recovery_plan.plan_id,
            status=NavigationStatus.IN_PROGRESS,
            visited_nodes=list(state.visited_nodes) + [recovery_plan.recovery_node_id],
        )
        await self._store.save_state(updated_state)

        await self._append_history_entry(
            session_id=session_id,
            node_id=recovery_plan.recovery_node_id,
            action=first_action,
            route=state.current_route,
        )

        return self._build_result(
            success=True,
            status=NavigationStatus.IN_PROGRESS,
            final_node_id=recovery_plan.recovery_node_id,
            executed_actions=list(recovery_plan.actions),
            steps_completed=1,
            steps_total=len(recovery_plan.actions),
            start_time=start_time,
        )

    async def _append_history_entry(
        self,
        session_id: UUID,
        node_id: UUID,
        action: NavigationAction | None,
        route: str | None,
    ) -> None:
        """Internal helper to append a NavigationHistoryEntry to session history.

        Args:
            session_id: Session identifier.
            node_id: Node identifier visited.
            action: Action executed.
            route: Route string visited.
        """
        history = await self.get_history(session_id)
        entry = NavigationHistoryEntry(
            node_id=node_id,
            action=action,
            route=route,
        )
        updated_history = NavigationHistory(
            session_id=session_id,
            entries=list(history.entries) + [entry],
        )
        await self._store.save_history(updated_history)

    def _build_result(
        self,
        success: bool,
        status: NavigationStatus,
        final_node_id: UUID | None,
        executed_actions: list[NavigationAction],
        steps_completed: int,
        steps_total: int,
        start_time: float,
        error: str | None = None,
    ) -> NavigationResult:
        """Internal helper to construct an immutable NavigationResult.

        Args:
            success: Boolean success flag.
            status: NavigationStatus enum.
            final_node_id: Target/current node ID.
            executed_actions: List of actions.
            steps_completed: Steps completed.
            steps_total: Total steps.
            start_time: Start benchmark time.
            error: Optional error description.

        Returns:
            NavigationResult: Constructed result instance.
        """
        duration = (time.perf_counter() - start_time) * 1000.0
        return NavigationResult(
            success=success,
            status=status,
            final_node_id=final_node_id,
            executed_actions=executed_actions,
            steps_completed=steps_completed,
            steps_total=steps_total,
            duration_ms=duration,
            error=error,
        )
