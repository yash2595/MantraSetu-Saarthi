"""Domain models and schemas for the Orchestrator subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 models, enums, execution steps, execution plans,
execution contexts, and execution results for workflow orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseOrchestratorModel(BaseModel):
    """Base Pydantic v2 model for immutable Orchestrator domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class ExecutionStatus(str, Enum):
    """Enumeration of execution lifecycle statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class ActionType(str, Enum):
    """Enumeration of workflow step action types."""

    AI = "ai"
    NAVIGATION = "navigation"
    BROWSER = "browser"
    TOOL = "tool"
    API = "api"
    WAIT = "wait"
    USER_INPUT = "user_input"


class ExecutionTarget(str, Enum):
    """Enumeration of target execution subsystems for step routing."""

    AI = "ai"
    NAVIGATION = "navigation"
    BROWSER = "browser"
    TOOL = "tool"
    SYSTEM = "system"


class ExecutionMetadata(BaseOrchestratorModel):
    """Domain model capturing metadata, tags, and custom attributes for orchestration entities.

    Attributes:
        source: Optional originating component or user string.
        tags: Immutable tuple of metadata tag strings.
        custom: Custom key-value pairs dictionary.
    """

    source: str | None = Field(
        default=None,
        description="Originating source identifier string.",
    )
    tags: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of tag strings.",
    )
    custom: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom key-value metadata dictionary.",
    )


class ExecutionStep(BaseOrchestratorModel):
    """Domain model representing a single step within an execution plan.

    Attributes:
        step_id: Unique step identifier UUID.
        action_type: ActionType enum categorizing step behavior.
        name: Short human-readable step name string.
        description: Detailed explanation of step goal.
        parameters: Action-specific parameter dictionary.
        dependencies: Tuple of step_id UUIDs that must complete before this step runs.
        timeout_ms: Step execution timeout in milliseconds.
        max_retries: Maximum retry attempts on transient failure.
        metadata: ExecutionMetadata instance.
    """

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique step identifier UUID.",
    )
    action_type: ActionType = Field(
        ...,
        description="ActionType enum categorizing step behavior.",
    )
    name: str = Field(
        ...,
        description="Short human-readable step name string.",
    )
    description: str = Field(
        default="",
        description="Detailed explanation of step goal.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameter dictionary.",
    )
    dependencies: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Tuple of step UUIDs required before execution.",
    )
    timeout_ms: int = Field(
        default=30000,
        gt=0,
        description="Step execution timeout in milliseconds.",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts on failure.",
    )
    metadata: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        description="ExecutionMetadata instance.",
    )


class ExecutionRequest(BaseOrchestratorModel):
    """Domain model representing a request to generate and execute an orchestration plan.

    Attributes:
        request_id: Unique request identifier UUID.
        goal: High-level task objective string.
        parameters: Target context or goal parameters dictionary.
        metadata: ExecutionMetadata instance.
        created_at: UTC creation timestamp.
    """

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier UUID.",
    )
    goal: str = Field(
        ...,
        description="High-level task objective string.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Goal parameter dictionary.",
    )
    metadata: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        description="ExecutionMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class ExecutionPlan(BaseOrchestratorModel):
    """Domain model representing an ordered DAG or sequence of ExecutionStep models.

    Attributes:
        plan_id: Unique plan identifier UUID.
        request_id: Associated request identifier UUID.
        steps: Immutable ordered tuple of ExecutionStep models.
        metadata: ExecutionMetadata instance.
        created_at: UTC creation timestamp.
    """

    plan_id: UUID = Field(
        default_factory=uuid4,
        description="Unique plan identifier UUID.",
    )
    request_id: UUID = Field(
        ...,
        description="Associated request identifier UUID.",
    )
    steps: tuple[ExecutionStep, ...] = Field(
        default_factory=tuple,
        description="Ordered tuple of ExecutionStep models.",
    )
    metadata: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        description="ExecutionMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class ExecutionResult(BaseOrchestratorModel):
    """Domain model representing the final outcome of an executed plan or step.

    Attributes:
        result_id: Unique result identifier UUID.
        plan_id: Associated plan identifier UUID.
        status: ExecutionStatus enum outcome.
        outputs: Execution output key-value dictionary.
        error: Diagnostic error string if failed.
        execution_time_ms: Total duration in milliseconds.
        metadata: ExecutionMetadata instance.
        created_at: UTC creation timestamp.
    """

    result_id: UUID = Field(
        default_factory=uuid4,
        description="Unique result identifier UUID.",
    )
    plan_id: UUID = Field(
        ...,
        description="Associated plan identifier UUID.",
    )
    status: ExecutionStatus = Field(
        ...,
        description="ExecutionStatus enum outcome.",
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution output key-value dictionary.",
    )
    error: str | None = Field(
        default=None,
        description="Diagnostic error string if failed.",
    )
    execution_time_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total duration in milliseconds.",
    )
    metadata: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        description="ExecutionMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class ExecutionContext(BaseOrchestratorModel):
    """Domain model capturing active execution state and shared runtime variables.

    Attributes:
        context_id: Unique context identifier UUID.
        plan_id: Associated execution plan UUID.
        current_step_id: Currently active step UUID.
        completed_step_ids: Immutable tuple of completed step UUIDs.
        shared_variables: Key-value runtime state variables.
        metadata: ExecutionMetadata instance.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    context_id: UUID = Field(
        default_factory=uuid4,
        description="Unique context identifier UUID.",
    )
    plan_id: UUID = Field(
        ...,
        description="Associated execution plan UUID.",
    )
    current_step_id: UUID | None = Field(
        default=None,
        description="Currently active step UUID.",
    )
    completed_step_ids: tuple[UUID, ...] = Field(
        default_factory=tuple,
        description="Tuple of completed step UUIDs.",
    )
    shared_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value runtime state variables.",
    )
    metadata: ExecutionMetadata = Field(
        default_factory=ExecutionMetadata,
        description="ExecutionMetadata instance.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )
