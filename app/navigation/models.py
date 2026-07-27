"""Domain models and schemas for the Navigation Intelligence subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for website nodes, navigation edges,
navigation plans, browser actions, and navigation context without Playwright or browser SDK coupling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseNavigationModel(BaseModel):
    """Base Pydantic v2 model for immutable Navigation domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class NavigationNodeType(str, Enum):
    """Enumeration of website map node types."""

    PAGE = "page"
    ACTION = "action"
    FORM = "form"
    EXTERNAL = "external"


class NavigationStatus(str, Enum):
    """Enumeration of navigation plan and action execution statuses."""

    PLANNED = "planned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ActionType(str, Enum):
    """Enumeration of web browser navigation action types."""

    CLICK = "click"
    INPUT = "input"
    SELECT = "select"
    NAVIGATE = "navigate"


class WebsiteNode(BaseNavigationModel):
    """Domain model representing a node (page/form) in a website structure map.

    Attributes:
        node_id: Unique website node identifier UUID.
        url: Page or target URL string.
        name: Human-readable name or label string.
        node_type: NavigationNodeType enum value.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC creation timestamp.
    """

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique website node identifier UUID.",
    )
    url: str = Field(
        ...,
        description="Page or target URL string.",
    )
    name: str = Field(
        ...,
        description="Human-readable name or label string.",
    )
    node_type: NavigationNodeType = Field(
        default=NavigationNodeType.PAGE,
        description="NavigationNodeType enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class NavigationEdge(BaseNavigationModel):
    """Domain model representing a transition edge connecting two WebsiteNode entities.

    Attributes:
        edge_id: Unique edge transition identifier UUID.
        source_node_id: Origin WebsiteNode identifier UUID.
        target_node_id: Destination WebsiteNode identifier UUID.
        action_type: ActionType enum causing the transition.
        action_data: Immutable transition parameters or selector mapping.
    """

    edge_id: UUID = Field(
        default_factory=uuid4,
        description="Unique edge transition identifier UUID.",
    )
    source_node_id: UUID = Field(
        ...,
        description="Origin WebsiteNode identifier UUID.",
    )
    target_node_id: UUID = Field(
        ...,
        description="Destination WebsiteNode identifier UUID.",
    )
    action_type: ActionType = Field(
        ...,
        description="ActionType enum causing the transition.",
    )
    action_data: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable transition parameters or selector mapping.",
    )


class NavigationPlan(BaseNavigationModel):
    """Domain model representing a multi-step goal navigation plan.

    Attributes:
        plan_id: Unique navigation plan identifier UUID.
        goal: Target goal description string.
        steps: Immutable tuple of step description strings.
        status: NavigationStatus enum indicating plan state.
        metadata: Immutable key-value metadata mapping.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique navigation plan identifier UUID.",
    )
    goal: str = Field(
        ...,
        description="Target goal description string.",
    )
    steps: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of step description strings.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PLANNED,
        description="NavigationStatus enum indicating plan state.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class NavigationAction(BaseNavigationModel):
    """Domain model representing an individual browser navigation command action.

    Attributes:
        action_id: Unique action identifier UUID.
        action_type: ActionType enum value.
        target: Target CSS selector, element text, or URL string.
        parameters: Immutable parameters mapping (e.g. input text value).
        status: NavigationStatus enum value.
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique action identifier UUID.",
    )
    action_type: ActionType = Field(
        ...,
        description="ActionType enum value.",
    )
    target: str = Field(
        ...,
        description="Target CSS selector, element text, or URL string.",
    )
    parameters: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable parameters mapping.",
    )
    status: NavigationStatus = Field(
        default=NavigationStatus.PLANNED,
        description="NavigationStatus enum value.",
    )


class NavigationContext(BaseNavigationModel):
    """Domain model capturing active navigation session context and page history.

    Attributes:
        session_id: Optional associated user session identifier UUID.
        current_url: Optional active browser page URL string.
        current_node: Optional active WebsiteNode entity.
        history: Immutable tuple of visited WebsiteNode entities.
        metadata: Immutable key-value metadata mapping.
    """

    session_id: UUID | None = Field(
        default=None,
        description="Optional associated user session identifier UUID.",
    )
    current_url: str | None = Field(
        default=None,
        description="Optional active browser page URL string.",
    )
    current_node: WebsiteNode | None = Field(
        default=None,
        description="Optional active WebsiteNode entity.",
    )
    history: tuple[WebsiteNode, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of visited WebsiteNode entities.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
