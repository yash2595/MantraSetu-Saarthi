"""Domain models and schemas for the Browser automation subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models, action enums, element references,
and session states for framework-independent browser interaction representations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Metadata = dict[str, Any]


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseBrowserModel(BaseModel):
    """Base Pydantic v2 model for immutable Browser domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class BrowserActionType(str, Enum):
    """Enumeration of supported browser action types."""

    GOTO = "goto"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    FILL = "fill"
    CLEAR = "clear"
    SELECT = "select"
    SELECT_OPTION = "select_option"
    CHECK = "check"
    UNCHECK = "uncheck"
    HOVER = "hover"
    SCROLL = "scroll"
    PRESS = "press"
    PRESS_KEY = "press_key"
    FOCUS = "focus"
    BLUR = "blur"
    DRAG = "drag"
    DROP = "drop"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    WAIT = "wait"
    WAIT_FOR_ELEMENT = "wait_for_element"
    WAIT_FOR_URL = "wait_for_url"
    WAIT_FOR_NETWORK_IDLE = "wait_for_network_idle"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_ATTRIBUTE = "extract_attribute"
    SCREENSHOT = "screenshot"
    CLOSE = "close"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"


class BrowserExecutionStatus(str, Enum):
    """Enumeration of browser action and batch execution statuses."""

    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class BrowserSessionStatus(str, Enum):
    """Enumeration of browser session operational statuses."""

    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    ERROR = "error"


class ElementReference(BaseBrowserModel):
    """Target web element reference domain model.

    Attributes:
        selector: CSS selector identifying the target element.
        xpath: Optional XPath expression identifying the target element.
        text: Optional text content associated with the element.
        tag_name: Optional HTML tag name of the element.
        visible: Optional visibility state flag.
        enabled: Optional enabled state flag.
        attributes: Dictionary of element HTML attributes.
    """

    selector: str = Field(
        ...,
        description="CSS selector identifying the target web element.",
    )
    xpath: str | None = Field(
        default=None,
        description="Optional XPath expression targeting the element.",
    )
    text: str | None = Field(
        default=None,
        description="Optional inner text content of the element.",
    )
    tag_name: str | None = Field(
        default=None,
        description="Optional HTML tag name of the element.",
    )
    visible: bool | None = Field(
        default=None,
        description="Optional visibility state flag of the element.",
    )
    enabled: bool | None = Field(
        default=None,
        description="Optional enabled state flag of the element.",
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        description="Dictionary of element HTML attributes.",
    )


class BrowserAction(BaseBrowserModel):
    """Domain model representing an individual browser action command.

    Attributes:
        action_id: Unique action identifier UUID.
        action_type: Type of browser action to perform.
        element: Optional target element reference.
        url: Optional target URL for navigation actions.
        value: Optional input value text or keystroke command.
        timeout_ms: Timeout duration in milliseconds.
        metadata: Arbitrary metadata key-value pairs.
        created_at: UTC creation timestamp.
    """

    action_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the browser action.",
    )
    action_type: BrowserActionType = Field(
        ...,
        description="Enumerated type of browser action.",
    )
    element: ElementReference | None = Field(
        default=None,
        description="Optional target web element reference.",
    )
    url: str | None = Field(
        default=None,
        description="Optional URL target for navigation actions.",
    )
    value: str | None = Field(
        default=None,
        description="Optional input value or key name for typing/selection.",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=0,
        description="Maximum execution timeout in milliseconds.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary action metadata dictionary.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class BrowserResult(BaseBrowserModel):
    """Domain model capturing the execution outcome of a browser action.

    Attributes:
        result_id: Unique result identifier UUID.
        action_id: Associated browser action identifier UUID.
        success: Boolean success status flag.
        status: Execution outcome status enum.
        url: Optional active URL after action execution.
        title: Optional active document title after execution.
        value: Optional extracted text or value result.
        screenshot_base64: Optional base64-encoded screenshot image data.
        error: Optional error description string if execution failed.
        duration_ms: Total execution duration in milliseconds.
        metadata: Arbitrary result metadata dictionary.
        executed_at: UTC execution completion timestamp.
    """

    result_id: UUID = Field(
        default_factory=uuid4,
        description="Unique result identifier.",
    )
    action_id: UUID = Field(
        ...,
        description="Associated browser action identifier UUID.",
    )
    success: bool = Field(
        ...,
        description="True if execution succeeded, False otherwise.",
    )
    status: BrowserExecutionStatus = Field(
        ...,
        description="Execution outcome status enum.",
    )
    url: str | None = Field(
        default=None,
        description="Active page URL after action execution.",
    )
    title: str | None = Field(
        default=None,
        description="Active document title after action execution.",
    )
    value: str | None = Field(
        default=None,
        description="Optional extracted text or value from action execution.",
    )
    screenshot_base64: str | None = Field(
        default=None,
        description="Optional base64-encoded screenshot image data.",
    )
    error: str | None = Field(
        default=None,
        description="Optional error description string if execution failed.",
    )
    duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total execution duration in milliseconds.",
    )
    metadata: Metadata = Field(
        default_factory=dict,
        description="Arbitrary result metadata dictionary.",
    )
    executed_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC timestamp when action execution completed.",
    )


class BrowserSession(BaseBrowserModel):
    """Domain model representing an active or historical browser session state.

    Attributes:
        session_id: Unique session identifier UUID.
        status: Current operational status of the browser session.
        current_url: Active page URL, if present.
        current_title: Active page document title, if present.
        user_agent: User-Agent string configured for the session.
        viewport_width: Viewport width in pixels.
        viewport_height: Viewport height in pixels.
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    session_id: UUID = Field(
        default_factory=uuid4,
        description="Unique session identifier UUID.",
    )
    status: BrowserSessionStatus = Field(
        default=BrowserSessionStatus.IDLE,
        description="Current operational status of the browser session.",
    )
    current_url: str | None = Field(
        default=None,
        description="Active page URL in the browser session.",
    )
    current_title: str | None = Field(
        default=None,
        description="Active document title in the browser session.",
    )
    user_agent: str | None = Field(
        default=None,
        description="Configured User-Agent string for the session.",
    )
    viewport_width: int = Field(
        default=1280,
        ge=1,
        description="Browser viewport width in pixels.",
    )
    viewport_height: int = Field(
        default=720,
        ge=1,
        description="Browser viewport height in pixels.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC session last update timestamp.",
    )


class BrowserBatch(BaseBrowserModel):
    """Domain model representing a batch sequence of browser actions.

    Attributes:
        batch_id: Unique batch identifier UUID.
        session_id: Target browser session identifier UUID.
        actions: Immutable tuple of BrowserAction commands to execute in sequence.
        status: Overall batch execution status.
        created_at: UTC creation timestamp.
    """

    batch_id: UUID = Field(
        default_factory=uuid4,
        description="Unique batch identifier UUID.",
    )
    session_id: UUID = Field(
        ...,
        description="Target browser session identifier UUID.",
    )
    actions: tuple[BrowserAction, ...] = Field(
        default_factory=tuple,
        description="Tuple of BrowserAction commands in execution sequence.",
    )
    status: BrowserExecutionStatus = Field(
        default=BrowserExecutionStatus.PENDING,
        description="Overall batch execution status.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC batch creation timestamp.",
    )
