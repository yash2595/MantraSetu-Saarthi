"""Domain models for the Navigation Intelligence module in MantraSetu AgentOS.

This module defines canonical domain models and enumerations representing navigation actions,
nodes, edges, states, history, plans, and execution results within the AgentOS platform architecture.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Metadata = dict[str, Any]


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class NavigationActionType(str, Enum):
    """Enumeration of supported navigation action types within AgentOS.

    Purpose:
        Categorizes atomic user interactions and control commands.

    Responsibility:
        Provides canonical string identifiers for browser bridge action dispatch.
    """

    CLICK = "CLICK"
    INPUT = "INPUT"
    SELECT = "SELECT"
    SUBMIT = "SUBMIT"
    BACK = "BACK"
    FORWARD = "FORWARD"
    OPEN = "OPEN"
    CLOSE = "CLOSE"
    SCROLL = "SCROLL"


class NavigationNodeType(str, Enum):
    """Enumeration of UI node categories for the navigation graph.

    Purpose:
        Classifies UI elements and layout containers in the target application.

    Responsibility:
        Supplies structural taxonomy for navigation planner reasoning.
    """

    PAGE = "PAGE"
    FORM = "FORM"
    MODAL = "MODAL"
    MENU = "MENU"
    SECTION = "SECTION"
    DIALOG = "DIALOG"
    POPUP = "POPUP"


class NavigationStatus(str, Enum):
    """Enumeration of navigation execution statuses.

    Purpose:
        Tracks session and plan lifecycle progress.

    Responsibility:
        Provides unified state status constants across engine components.
    """

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class BaseNavigationModel(BaseModel):
    """Base Pydantic model for immutable Navigation domain entities.

    Purpose:
        Establishes strict validation rules and immutability across domain entities.

    Responsibility:
        Configures Pydantic v2 immutability, extra field forbidden enforcement,
        and name population defaults.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class BaseAuditModel(BaseNavigationModel):
    """Base model for domain entities requiring creation and modification auditing.

    Purpose:
        Standardizes audit timestamps across persistent entities.

    Responsibility:
        Encapsulates created_at and updated_at UTC timestamp fields.
    """

    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when the entity was created.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when the entity was last updated.",
    )


class NavigationAction(BaseAuditModel):
    """Domain model representing a discrete navigation action or user interaction.

    Purpose:
        Encapsulates a single atomic UI interaction command.

    Responsibility:
        Maintains target element selectors, payload values, metadata, and action types.

    Usage:
        Instantiated by planners or action engines to command browser interactions.

    Attributes:
        action_id: Unique identifier for the navigation action.
        action_type: Category of action to execute.
        target: Target selector, element identifier, or URI route.
        value: Optional input value or payload associated with the action.
        metadata: Arbitrary contextual metadata dictionary.
        created_at: UTC timestamp when the action was created.
        updated_at: UTC timestamp when the action was last updated.
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the navigation action.",
    )
    action_type: NavigationActionType = Field(
        ...,
        description="Category of navigation action to execute.",
    )
    target: str = Field(
        ...,
        min_length=1,
        description="Target element selector, component identifier, or route URI.",
    )
    value: str | None = Field(
        default=None,
        description="Optional payload, input text, or parameter value for the action.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary metadata payload associated with the action.",
    )

    @field_validator("target", mode="after")
    @classmethod
    def validate_target(cls, value: str) -> str:
        """Validate target is not empty or whitespace-only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("NavigationAction.target cannot be blank.")
        return cleaned


class NavigationNode(BaseAuditModel):
    """Domain model representing a discrete state, route, or vertex in a navigation graph.

    Purpose:
        Defines a single navigational UI state or route endpoint.

    Responsibility:
        Holds route descriptions, classification, titles, and hierarchical metadata.

    Usage:
        Used by NavigationGraph to construct application topology.

    Note:
        parent_node_id and child_node_ids represent optional UI hierarchy references.
        NavigationGraph remains the single source of truth for graph navigation relationships.

    Attributes:
        node_id: Unique identifier for the navigation node.
        name: Logical name of the node.
        route: URI, path, or route identifier.
        node_type: Category or UI type of the navigation node.
        title: Optional human-readable display title.
        description: Optional descriptive text for the node.
        parent_node_id: Optional parent node identifier in hierarchical graphs.
        child_node_ids: List of child node identifiers linked from this node.
        metadata: Arbitrary contextual metadata dictionary.
        created_at: UTC timestamp when the node was created.
        updated_at: UTC timestamp when the node was last updated.
    """

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the navigation node.",
    )
    name: str = Field(
        ...,
        description="Logical name or functional identifier of the node.",
    )
    route: str = Field(
        ...,
        description="URI, path pattern, or route identifier.",
    )
    node_type: NavigationNodeType = Field(
        ...,
        description="Category or UI type of the navigation node.",
    )
    title: str | None = Field(
        default=None,
        description="Optional human-readable title for the page or state.",
    )
    description: str | None = Field(
        default=None,
        description="Optional detailed description of the node.",
    )
    parent_node_id: UUID | None = Field(
        default=None,
        description="Optional parent navigation node identifier.",
    )
    child_node_ids: list[UUID] = Field(
        default_factory=list,
        description="List of child navigation node identifiers.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary contextual metadata dictionary.",
    )

    @field_validator("name", mode="after")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate node name is not empty or whitespace-only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("NavigationNode.name cannot be blank.")
        return cleaned

    @field_validator("route", mode="after")
    @classmethod
    def validate_route(cls, value: str) -> str:
        """Validate route is not empty or whitespace-only."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("NavigationNode.route cannot be blank.")
        return cleaned


class NavigationEdge(BaseAuditModel):
    """Domain model representing a directed edge/transition between two navigation nodes.

    Purpose:
        Defines a valid transition path between two navigation graph nodes.

    Responsibility:
        Encapsulates source node, destination node, transition action, cost weight, and transition metadata.

    Usage:
        Utilized in pathfinding algorithms and graph building.

    Attributes:
        edge_id: Unique identifier for the navigation edge.
        source_node_id: Originating navigation node identifier.
        destination_node_id: Target navigation node identifier.
        action: Navigation action required to transition along this edge.
        weight: Cost or weight assigned to this edge transition.
        metadata: Arbitrary edge metadata for transition constraints and flags.
        created_at: UTC timestamp when the edge was created.
        updated_at: UTC timestamp when the edge was last updated.
    """

    edge_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the navigation edge.",
    )
    source_node_id: UUID = Field(
        ...,
        description="Identifier of the source navigation node.",
    )
    destination_node_id: UUID = Field(
        ...,
        description="Identifier of the destination navigation node.",
    )
    action: NavigationAction = Field(
        ...,
        description="Navigation action executed to transition across this edge.",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Traversal cost associated with this navigation edge.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary contextual metadata payload associated with this edge.",
    )


class NavigationState(BaseNavigationModel):
    """Domain model representing the real-time active state of a navigation session.

    Purpose:
        Captures transient runtime state for an active agent navigation session.

    Responsibility:
        Tracks session status, current node, route, executing action, active plan ID, and runtime metadata.

    Usage:
        Maintained in memory or storage by session management services.

    Attributes:
        session_id: Unique navigation session identifier.
        current_node_id: Optional current active node identifier.
        current_route: Optional current active route string.
        current_action: Optional navigation action currently being executed.
        current_plan_id: Optional active navigation plan identifier.
        status: Status of the navigation session.
        visited_nodes: Ordered list of visited node identifiers.
        metadata: Arbitrary runtime execution metadata dictionary.
        updated_at: UTC timestamp when the state was last updated.
    """

    session_id: UUID = Field(
        ...,
        description="Unique navigation session identifier.",
    )
    current_node_id: UUID | None = Field(
        default=None,
        description="Identifier of the currently active navigation node.",
    )
    current_route: str | None = Field(
        default=None,
        description="Current route path or URI.",
    )
    current_action: NavigationAction | None = Field(
        default=None,
        description="Navigation action currently being executed.",
    )
    current_plan_id: UUID | None = Field(
        default=None,
        description="Identifier of the active navigation plan being executed.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PENDING,
        description="Current lifecycle status of the navigation session.",
    )
    visited_nodes: list[UUID] = Field(
        default_factory=list,
        description="Chronological record of visited navigation node identifiers.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary runtime execution metadata dictionary.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp of the last state update.",
    )


class NavigationHistoryEntry(BaseNavigationModel):
    """Domain model representing a single entry in a navigation history log.

    Purpose:
        Provides an immutable snapshot of a single historical navigation step.

    Responsibility:
        Stores step timestamps, visited node ID, executed action, route, and contextual metadata.

    Usage:
        Appended sequentially into session navigation audit logs.

    Attributes:
        node_id: Identifier of the node associated with this history entry.
        route: Optional route string associated with this step.
        action: Optional navigation action executed at this step.
        metadata: Arbitrary metadata payload associated with this history entry.
        timestamp: UTC timestamp when the history entry was recorded.
    """

    node_id: UUID = Field(
        ...,
        description="Identifier of the node visited or associated with this step.",
    )
    route: str | None = Field(
        default=None,
        description="Optional route URI path associated with this historical step.",
    )
    action: NavigationAction | None = Field(
        default=None,
        description="Optional navigation action executed at this history step.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary metadata payload associated with this history entry.",
    )
    timestamp: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when this history entry was recorded.",
    )


class NavigationHistory(BaseNavigationModel):
    """Domain model maintaining an execution history of navigation entries.

    Purpose:
        Aggregates session execution history.

    Responsibility:
        Stores sequential NavigationHistoryEntry objects for session audit logging.

    Usage:
        Used for playback, auditing, and session replay analytics.

    Attributes:
        session_id: Unique navigation session identifier.
        entries: Chronological record of navigation history entries.
    """

    session_id: UUID = Field(
        ...,
        description="Unique navigation session identifier.",
    )
    entries: list[NavigationHistoryEntry] = Field(
        default_factory=list,
        description="Chronological record of navigation history entries.",
    )


class NavigationPlan(BaseAuditModel):
    """Domain model representing a structured sequence of actions planned to reach a node.

    Purpose:
        Defines an execution manifest produced by a navigation planner.

    Responsibility:
        Holds plan metadata, source/target nodes, lifecycle status, action sequence, and cost estimates.

    Usage:
        Generated by planners and consumed by execution orchestrators.

    Attributes:
        plan_id: Unique identifier for the navigation plan.
        source_node_id: Originating node identifier where the plan starts.
        target_node_id: Destination node identifier targeted by the plan.
        status: Current lifecycle status of the navigation plan.
        actions: Ordered list of actions forming the navigation sequence.
        estimated_cost: Optional planner estimate of total traversal cost.
        estimated_steps: Optional planner estimate of total step count.
        created_at: UTC timestamp when the plan was generated.
        updated_at: UTC timestamp when the plan was last updated.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the navigation plan.",
    )
    source_node_id: UUID = Field(
        ...,
        description="Originating node identifier where the navigation plan starts.",
    )
    target_node_id: UUID = Field(
        ...,
        description="Destination node identifier targeted by the plan.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PENDING,
        description="Current execution status of the navigation plan.",
    )
    actions: list[NavigationAction] = Field(
        default_factory=list,
        description="Ordered sequence of planned navigation actions.",
    )
    estimated_cost: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional planner estimate of total traversal cost.",
    )
    estimated_steps: int | None = Field(
        default=None,
        ge=0,
        description="Optional planner estimate of total step count.",
    )


class NavigationResult(BaseNavigationModel):
    """Domain model representing the execution outcome of a navigation sequence or plan.

    Purpose:
        Summarizes the finalized telemetry of a navigation attempt.

    Responsibility:
        Encapsulates success boolean, status enum, metrics, step totals, and error details.

    Usage:
        Returned by orchestrators to callers upon navigation completion or failure.

    Attributes:
        success: True if navigation succeeded, False otherwise.
        status: NavigationStatus reflecting execution outcome.
        final_node_id: Optional final node identifier reached upon execution.
        executed_actions: List of actions successfully executed during the run.
        steps_completed: Total number of navigation steps completed.
        steps_total: Total number of navigation steps scheduled.
        duration_ms: Total execution duration in milliseconds.
        error: Optional error string or failure cause description.
        completed_at: UTC timestamp when execution finalized.
    """

    success: bool = Field(
        ...,
        description="Indicates whether the navigation execution succeeded.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.COMPLETED,
        description="NavigationStatus lifecycle state for the execution result.",
    )
    final_node_id: UUID | None = Field(
        default=None,
        description="Identifier of the final navigation node reached.",
    )
    executed_actions: list[NavigationAction] = Field(
        default_factory=list,
        description="List of navigation actions executed during the run.",
    )
    steps_completed: int = Field(
        default=0,
        ge=0,
        description="Total number of navigation steps completed.",
    )
    steps_total: int = Field(
        default=0,
        ge=0,
        description="Total number of navigation steps scheduled.",
    )
    duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in milliseconds.",
    )
    error: str | None = Field(
        default=None,
        description="Error detail or failure explanation if navigation failed.",
    )
    completed_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when the navigation execution completed.",
    )

    @model_validator(mode="after")
    def validate_status_success_consistency(self) -> "NavigationResult":
        """Validate logical consistency between status and success boolean."""
        if self.status == NavigationStatus.COMPLETED and not self.success:
            raise ValueError(
                "NavigationResult cannot have status COMPLETED when success is False."
            )
        if self.status == NavigationStatus.FAILED and self.success:
            raise ValueError(
                "NavigationResult cannot have status FAILED when success is True."
            )
        return self
