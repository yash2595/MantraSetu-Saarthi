"""Navigation Backtracking and Recovery domain module for MantraSetu AgentOS.

This module provides the NavigationBacktracker domain service, RecoveryAnalysis, and RecoveryPlan
models to construct recovery plans when navigation sessions encounter loops or invalid states,
without executing browser actions or mutating graph and storage states.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.navigation.analyzer import NavigationAnalyzer
from app.navigation.graph import NavigationGraph
from app.navigation.models import (
    NavigationAction,
    NavigationActionType,
    NavigationHistory,
)
from app.navigation.store import BaseNavigationStore


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseBacktrackingModel(BaseModel):
    """Base Pydantic model for immutable Backtracking domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class BacktrackingError(Exception):
    """Base domain exception raised when backtracking or recovery analysis fails."""

    pass


class NoRecoveryPointFoundError(BacktrackingError):
    """Raised when no safe historical recovery node can be identified."""

    pass


class RecoveryAnalysis(BaseBacktrackingModel):
    """Domain model summarizing recovery and backtracking analysis for a session.

    Attributes:
        session_id: Unique session identifier.
        loop_detected: True if a navigation loop is active in session history.
        recovery_node_id: Identifier of the target recovery node, if found.
        reason: Diagnostic description string explaining analysis findings.
    """

    session_id: UUID = Field(
        ...,
        description="Unique session identifier being analyzed for recovery.",
    )
    loop_detected: bool = Field(
        ...,
        description="True if a navigation loop is active, False otherwise.",
    )
    recovery_node_id: UUID | None = Field(
        default=None,
        description="Identifier of the target recovery node, if identified.",
    )
    reason: str | None = Field(
        default=None,
        description="Diagnostic description string explaining analysis findings.",
    )


class RecoveryPlan(BaseBacktrackingModel):
    """Domain model representing a constructed recovery action plan manifest.

    Attributes:
        plan_id: Unique identifier for the recovery plan.
        session_id: Unique session identifier.
        recovery_node_id: Target recovery node identifier.
        actions: Tuple of navigation actions to execute for recovery.
        created_at: UTC timestamp when the recovery plan was generated.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the recovery plan.",
    )
    session_id: UUID = Field(
        ...,
        description="Unique session identifier.",
    )
    recovery_node_id: UUID = Field(
        ...,
        description="Target recovery node identifier.",
    )
    actions: tuple[NavigationAction, ...] = Field(
        default_factory=tuple,
        description="Tuple of navigation actions to execute for recovery.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when the recovery plan was generated.",
    )


class NavigationBacktracker:
    """Domain service responsible for generating session recovery and backtracking plans.

    Responsibility:
        Analyzes session history to identify safe recovery points and constructs immutable RecoveryPlan
        manifests without executing browser automation, mutating graph topology, or altering storage state.
    """

    def __init__(
        self,
        graph: NavigationGraph,
        store: BaseNavigationStore,
        analyzer: NavigationAnalyzer,
    ) -> None:
        """Initialize NavigationBacktracker with graph, store, and analyzer dependencies.

        Args:
            graph: NavigationGraph instance.
            store: BaseNavigationStore instance.
            analyzer: NavigationAnalyzer instance.
        """
        self._graph = graph
        self._store = store
        self._analyzer = analyzer

    async def initialize(self) -> None:
        """Initialize backtracker resources (no-op)."""
        return None

    async def close(self) -> None:
        """Close backtracker resources (no-op)."""
        return None

    async def recovery_required(self, session_id: UUID) -> bool:
        """Check whether a session requires recovery due to active loops or repeated states.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            bool: True if recovery is required, False otherwise.
        """
        history = await self._load_history(session_id)
        return await self._analyzer.should_backtrack(history)

    async def can_recover(self, session_id: UUID) -> bool:
        """Determine whether a valid recovery plan can be constructed for a session.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            bool: True if a safe recovery point exists in the graph, False otherwise.
        """
        history = await self._load_history(session_id)
        analysis = self._analyze_recovery(session_id, history)
        if not analysis.recovery_node_id:
            return False
        return self._graph.has_node(analysis.recovery_node_id)

    async def create_recovery_plan(self, session_id: UUID) -> RecoveryPlan:
        """Construct a RecoveryPlan to return the session to a safe historical node.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            RecoveryPlan: Constructed recovery plan manifest.

        Raises:
            NoRecoveryPointFoundError: If no safe recovery node can be identified or if the node
                no longer exists in the navigation graph.
        """
        history = await self._load_history(session_id)
        analysis = self._analyze_recovery(session_id, history)

        if not analysis.recovery_node_id:
            raise NoRecoveryPointFoundError(
                f"No safe recovery point found for session {session_id}: {analysis.reason}"
            )

        if not self._graph.has_node(analysis.recovery_node_id):
            raise NoRecoveryPointFoundError(
                f"Recovery target node {analysis.recovery_node_id} no longer exists in navigation graph."
            )

        back_action = NavigationAction(
            action_type=NavigationActionType.BACK,
            target="HISTORY_BACK",
            value=str(analysis.recovery_node_id),
        )

        return self._build_recovery_plan(
            session_id=session_id,
            recovery_node_id=analysis.recovery_node_id,
            actions=[back_action],
        )

    async def _load_history(self, session_id: UUID) -> NavigationHistory | None:
        """Internal helper to retrieve session history from storage.

        Args:
            session_id: Unique navigation session identifier.

        Returns:
            NavigationHistory | None: Retrieved history instance or None.
        """
        return await self._store.get_history(session_id)

    def _analyze_recovery(
        self,
        session_id: UUID,
        history: NavigationHistory | None,
    ) -> RecoveryAnalysis:
        """Internal helper to analyze session history and construct a RecoveryAnalysis.

        Args:
            session_id: Unique navigation session identifier.
            history: Optional NavigationHistory instance.

        Returns:
            RecoveryAnalysis: Consolidated recovery analysis result.
        """
        if not history or not history.entries:
            return RecoveryAnalysis(
                session_id=session_id,
                loop_detected=False,
                recovery_node_id=None,
                reason="No session history entries available.",
            )

        recovery_node_id = self._find_recovery_node(history)
        loop_detected = recovery_node_id is not None

        return RecoveryAnalysis(
            session_id=session_id,
            loop_detected=loop_detected,
            recovery_node_id=recovery_node_id,
            reason="Recovery node identified from session history."
            if recovery_node_id
            else "No recovery node found.",
        )

    def _find_recovery_node(self, history: NavigationHistory) -> UUID | None:
        """Identify the last known non-looping node in history.

        Sprint 1 Recovery Heuristic:
            Scans chronological history entries to locate the first repeated node visit and selects
            the preceding node as the recovery target. If no repetition is found, defaults to the
            first recorded entry in history. Future implementations may replace this strategy with
            advanced AI-driven or graph-aware recovery algorithms.

        Args:
            history: NavigationHistory instance to analyze.

        Returns:
            UUID | None: Recovery node identifier if found, None otherwise.
        """
        if not history.entries:
            return None

        seen: set[UUID] = set()
        first_repeated_index: int | None = None

        for idx, entry in enumerate(history.entries):
            if entry.node_id in seen:
                first_repeated_index = idx
                break
            seen.add(entry.node_id)

        if first_repeated_index is not None and first_repeated_index > 0:
            return history.entries[first_repeated_index - 1].node_id

        return history.entries[0].node_id

    def _build_recovery_plan(
        self,
        session_id: UUID,
        recovery_node_id: UUID,
        actions: list[NavigationAction],
    ) -> RecoveryPlan:
        """Internal helper to construct a RecoveryPlan instance.

        Args:
            session_id: Unique session identifier.
            recovery_node_id: Target recovery node identifier.
            actions: List of recovery actions.

        Returns:
            RecoveryPlan: Constructed recovery plan model.
        """
        return RecoveryPlan(
            session_id=session_id,
            recovery_node_id=recovery_node_id,
            actions=tuple(actions),
        )
