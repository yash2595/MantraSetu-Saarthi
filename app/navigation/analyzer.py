"""Read-only Navigation Analyzer domain service for MantraSetu AgentOS.

This module provides non-mutating analysis of navigation states, state consistency,
action availability, history loop detection, and goal node alignment without performing
graph traversal algorithms, plan generation, or browser execution.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.navigation.graph import NavigationGraph
from app.navigation.models import (
    NavigationAction,
    NavigationHistory,
    NavigationNode,
    NavigationState,
    NavigationStatus,
)
from app.navigation.store import BaseNavigationStore


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseAnalyzerModel(BaseModel):
    """Base Pydantic model for immutable Navigation Analyzer objects."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ValidationResult(BaseAnalyzerModel):
    """Result model for navigation state validation checks.

    Attributes:
        valid: True if state is valid, False otherwise.
        errors: Tuple of error strings describing validation issues.
    """

    valid: bool = Field(
        ...,
        description="True if state validation succeeded, False otherwise.",
    )
    errors: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Tuple of validation error descriptions.",
    )


class GoalAnalysis(BaseAnalyzerModel):
    """Analysis model evaluating goal presence and current alignment.

    Attributes:
        target_exists: True if target node exists in the navigation graph.
        current_node_exists: True if current node exists in the navigation graph.
        already_at_target: True if current node matches target node.
        reason: Optional diagnostic explanation string.
    """

    target_exists: bool = Field(
        ...,
        description="True if target node exists in the navigation graph.",
    )
    current_node_exists: bool = Field(
        ...,
        description="True if current node exists in the navigation graph.",
    )
    already_at_target: bool = Field(
        ...,
        description="True if current node matches target node.",
    )
    reason: str | None = Field(
        default=None,
        description="Optional diagnostic explanation string.",
    )


class LoopAnalysis(BaseAnalyzerModel):
    """Analysis model evaluating navigation history for repeating loops.

    Attributes:
        loop_detected: True if a navigation loop is detected in history.
        repeated_nodes: Tuple of node IDs that form the detected loop.
    """

    loop_detected: bool = Field(
        ...,
        description="True if a navigation loop is detected, False otherwise.",
    )
    repeated_nodes: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Tuple of node IDs involved in the detected loop.",
    )


class NavigationAnalysis(BaseAnalyzerModel):
    """Comprehensive domain model for session navigation analysis.

    Attributes:
        session_id: Unique session identifier.
        current_node: Current active node instance, if resolved.
        visited_nodes: Tuple of visited node IDs.
        available_actions: Tuple of available outgoing actions from current node.
        validation: ValidationResult model.
        goal: GoalAnalysis model, if target was evaluated.
        loop: LoopAnalysis model.
        analyzed_at: UTC timestamp when analysis was conducted.
    """

    session_id: UUID = Field(
        ...,
        description="Unique session identifier being analyzed.",
    )
    current_node: NavigationNode | None = Field(
        default=None,
        description="Current active node instance, if present in graph.",
    )
    visited_nodes: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Tuple of visited node IDs in chronological order.",
    )
    available_actions: tuple[NavigationAction, ...] = Field(
        default_factory=tuple,
        description="Tuple of outgoing navigation actions available from current node.",
    )
    validation: ValidationResult = Field(
        ...,
        description="Validation result for the session state.",
    )
    goal: GoalAnalysis | None = Field(
        default=None,
        description="Optional goal analysis evaluation if target node was supplied.",
    )
    loop: LoopAnalysis = Field(
        ...,
        description="Loop analysis evaluation based on session history.",
    )
    analyzed_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when analysis was conducted.",
    )


class NavigationAnalyzer:
    """Read-only domain service for analyzing navigation states, goals, and history.

    Responsibility:
        Performs read-only state validation, action availability resolution, goal alignment checks,
        and loop detection using NavigationGraph and BaseNavigationStore without modifying state or graph topology.
    """

    def __init__(self, graph: NavigationGraph, store: BaseNavigationStore) -> None:
        """Initialize NavigationAnalyzer with graph and store dependencies.

        Args:
            graph: NavigationGraph instance for route topology lookup.
            store: BaseNavigationStore instance for session state and history retrieval.
        """
        self._graph = graph
        self._store = store

    async def initialize(self) -> None:
        """Initialize analyzer resources (no-op)."""
        pass

    async def close(self) -> None:
        """Close analyzer resources (no-op)."""
        pass

    async def validate_state(self, state: NavigationState) -> ValidationResult:
        """Validate an active NavigationState against graph contents, route, plan, and status.

        Args:
            state: The NavigationState instance to validate.

        Returns:
            ValidationResult: Validation outcome and list of errors if any.
        """
        errors: list[str] = []

        if state.current_node_id:
            node = self._graph.get_node(state.current_node_id)
            if not node:
                errors.append(
                    f"Current node_id {state.current_node_id} does not exist in graph."
                )
            elif state.current_route and state.current_route != node.route:
                errors.append(
                    f"Current route '{state.current_route}' does not match graph node route '{node.route}'."
                )

        if state.current_plan_id:
            plan = await self._store.get_plan(state.current_plan_id)
            if not plan:
                errors.append(
                    f"Current plan_id {state.current_plan_id} does not exist in store."
                )

        if not isinstance(state.status, NavigationStatus):
            errors.append(f"Invalid navigation status: {state.status}.")

        for visited_id in state.visited_nodes:
            if not self._graph.has_node(visited_id):
                errors.append(
                    f"Visited node_id {visited_id} does not exist in graph."
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=tuple(errors),
        )

    async def analyze_goal(
        self,
        current_node_id: UUID | None,
        target_node_id: UUID | None,
    ) -> GoalAnalysis:
        """Evaluate presence and match status of current and target nodes.

        Planner is solely responsible for determining whether a destination is reachable.

        Args:
            current_node_id: Identifier of the current active node.
            target_node_id: Identifier of the intended target node.

        Returns:
            GoalAnalysis: Evaluation of target existence, current node existence, and match state.
        """
        if not target_node_id:
            return GoalAnalysis(
                target_exists=False,
                current_node_exists=bool(current_node_id and self._graph.has_node(current_node_id)),
                already_at_target=False,
                reason="No target_node_id specified.",
            )

        target_exists = self._graph.has_node(target_node_id)
        current_exists = bool(current_node_id and self._graph.has_node(current_node_id))
        already_at = bool(current_node_id and target_node_id and current_node_id == target_node_id)

        if not target_exists:
            reason = f"Target node_id {target_node_id} does not exist in graph."
        elif already_at:
            reason = "Current node matches target node."
        elif not current_exists:
            reason = "Current node is unknown or missing from graph."
        else:
            reason = "Target and current nodes exist; reachability is determined by Planner."

        return GoalAnalysis(
            target_exists=target_exists,
            current_node_exists=current_exists,
            already_at_target=already_at,
            reason=reason,
        )

    async def detect_loop(self, history: NavigationHistory | None) -> LoopAnalysis:
        """Analyze navigation history entries to detect repeating node visit loops.

        Args:
            history: Optional NavigationHistory instance.

        Returns:
            LoopAnalysis: Evaluation indicating whether a loop was detected.
        """
        if not history or not history.entries:
            return LoopAnalysis(loop_detected=False, repeated_nodes=())

        visited_sequence = [entry.node_id for entry in history.entries]
        seen: set[UUID] = set()
        repeated: list[UUID] = []

        for node_id in visited_sequence:
            if node_id in seen:
                if node_id not in repeated:
                    repeated.append(node_id)
            else:
                seen.add(node_id)

        return LoopAnalysis(
            loop_detected=len(repeated) > 0,
            repeated_nodes=tuple(repeated),
        )

    async def available_actions(
        self, node_id: UUID | None
    ) -> tuple[NavigationAction, ...]:
        """Resolve available outgoing navigation actions from a given node using graph API.

        Args:
            node_id: Identifier of the node.

        Returns:
            tuple[NavigationAction, ...]: Tuple of NavigationAction objects.
        """
        if not node_id:
            return ()
        return self._graph.get_outgoing_actions(node_id)

    async def is_navigation_complete(self, state: NavigationState) -> bool:
        """Check whether session state indicates completed navigation.

        Args:
            state: The NavigationState instance to check.

        Returns:
            bool: True if status is COMPLETED, False otherwise.
        """
        return state.status == NavigationStatus.COMPLETED

    async def should_backtrack(self, history: NavigationHistory | None) -> bool:
        """Determine if recent history suggests a loop or repeated state requiring backtracking.

        Args:
            history: Optional NavigationHistory instance.

        Returns:
            bool: True if a loop is detected in recent history, False otherwise.
        """
        loop = await self.detect_loop(history)
        return loop.loop_detected

    async def analyze_session(
        self,
        session_id: UUID,
        target_node_id: UUID | None = None,
    ) -> NavigationAnalysis:
        """Perform comprehensive read-only analysis of a navigation session.

        Args:
            session_id: Unique navigation session identifier.
            target_node_id: Optional destination node ID to evaluate goal alignment.

        Returns:
            NavigationAnalysis: Consolidated analysis results for the session.
        """
        state = await self._store.get_state(session_id)
        history = await self._store.get_history(session_id)

        if not state:
            state = NavigationState(session_id=session_id)

        validation = await self.validate_state(state)
        loop = await self.detect_loop(history)
        goal = await self.analyze_goal(state.current_node_id, target_node_id) if target_node_id else None

        current_node = self._graph.get_node(state.current_node_id) if state.current_node_id else None
        actions = await self.available_actions(state.current_node_id)

        return NavigationAnalysis(
            session_id=session_id,
            current_node=current_node,
            visited_nodes=tuple(state.visited_nodes),
            available_actions=actions,
            validation=validation,
            goal=goal,
            loop=loop,
        )
