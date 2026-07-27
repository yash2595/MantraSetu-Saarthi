"""Browser Executor module for MantraSetu AgentOS.

This module implements BrowserExecutor for dispatching and executing browser action commands,
action batches, and error translation without creating sessions or managing session lifecycles.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Coroutine
from uuid import UUID

from app.browser.base import (
    ActionExecutionError,
    BaseBrowserExecutor,
    BaseBrowserSession,
    BatchExecutionError,
    BrowserRuntimeHandle,
)
from app.browser.models import (
    BrowserAction,
    BrowserActionType,
    BrowserBatch,
    BrowserExecutionStatus,
    BrowserResult,
)


class BrowserExecutor(BaseBrowserExecutor):
    """Action executor implementing BaseBrowserExecutor contract.

    Responsibility:
        Dispatches individual BrowserAction commands and sequential BrowserBatch workflows to
        action execution handlers, translating failures into domain-specific exceptions.
    """

    def __init__(self, session_manager: BaseBrowserSession) -> None:
        """Initialize BrowserExecutor with injected BaseBrowserSession dependency.

        Args:
            session_manager: BaseBrowserSession implementation managing session lifecycle.
        """
        self._session_manager = session_manager
        self._initialized = False
        self._cancelled_sessions: set[UUID] = set()

        # Dispatch table mapping BrowserActionType to handler coroutines
        self._handlers: dict[
            BrowserActionType,
            Callable[[UUID, BrowserAction, BrowserRuntimeHandle], Coroutine[Any, Any, BrowserResult]],
        ] = {
            BrowserActionType.GOTO: self._execute_goto,
            BrowserActionType.CLICK: self._execute_click,
            BrowserActionType.DOUBLE_CLICK: self._execute_double_click,
            BrowserActionType.RIGHT_CLICK: self._execute_right_click,
            BrowserActionType.TYPE: self._execute_type,
            BrowserActionType.FILL: self._execute_fill,
            BrowserActionType.CLEAR: self._execute_clear,
            BrowserActionType.SELECT: self._execute_select,
            BrowserActionType.SELECT_OPTION: self._execute_select_option,
            BrowserActionType.CHECK: self._execute_check,
            BrowserActionType.UNCHECK: self._execute_uncheck,
            BrowserActionType.HOVER: self._execute_hover,
            BrowserActionType.SCROLL: self._execute_scroll,
            BrowserActionType.PRESS: self._execute_press,
            BrowserActionType.PRESS_KEY: self._execute_press_key,
            BrowserActionType.FOCUS: self._execute_focus,
            BrowserActionType.BLUR: self._execute_blur,
            BrowserActionType.DRAG: self._execute_drag,
            BrowserActionType.DROP: self._execute_drop,
            BrowserActionType.UPLOAD: self._execute_upload,
            BrowserActionType.DOWNLOAD: self._execute_download,
            BrowserActionType.WAIT: self._execute_wait,
            BrowserActionType.WAIT_FOR_ELEMENT: self._execute_wait_for_element,
            BrowserActionType.WAIT_FOR_URL: self._execute_wait_for_url,
            BrowserActionType.WAIT_FOR_NETWORK_IDLE: self._execute_wait_for_network_idle,
            BrowserActionType.EXTRACT_TEXT: self._execute_extract_text,
            BrowserActionType.EXTRACT_ATTRIBUTE: self._execute_extract_attribute,
            BrowserActionType.SCREENSHOT: self._execute_screenshot,
            BrowserActionType.CLOSE: self._execute_close,
            BrowserActionType.BACK: self._execute_back,
            BrowserActionType.FORWARD: self._execute_forward,
            BrowserActionType.RELOAD: self._execute_reload,
        }

    async def initialize(self) -> None:
        """Initialize executor runtime state."""
        self._initialized = True

    async def close(self) -> None:
        """Close executor state and reset cancellations."""
        self._cancelled_sessions.clear()
        self._initialized = False

    async def health_check(self) -> bool:
        """Check operational health of the executor and session manager dependency.

        Returns:
            bool: True if executor is initialized and session manager is healthy.
        """
        if not self._initialized:
            return False
        return await self._session_manager.health_check()

    async def cancel(self, session_id: UUID) -> None:
        """Register a cancellation request for ongoing actions in a session.

        Args:
            session_id: Unique session identifier UUID to cancel.
        """
        self._cancelled_sessions.add(session_id)

    async def execute_action(
        self,
        session_id: UUID,
        action: BrowserAction,
    ) -> BrowserResult:
        """Execute a single browser action command.

        Args:
            session_id: Target session identifier UUID.
            action: BrowserAction command to execute.

        Returns:
            BrowserResult: Immutable execution result model.

        Raises:
            ActionExecutionError: If session runtime is missing, uninitialized, or action fails.
        """
        if not self._initialized:
            raise ActionExecutionError("BrowserExecutor is not initialized.")

        if session_id in self._cancelled_sessions:
            self._cancelled_sessions.remove(session_id)
            return self._build_result(
                action_id=action.action_id,
                success=False,
                status=BrowserExecutionStatus.CANCELLED,
                error=f"Execution cancelled for session {session_id}.",
            )

        handle = await self._session_manager.get_runtime_handle(session_id)
        if not handle:
            raise ActionExecutionError(
                f"Active runtime handle for session {session_id} not found."
            )

        return await self._dispatch_action(session_id, action, handle)

    async def execute_batch(
        self,
        session_id: UUID,
        batch: BrowserBatch,
    ) -> tuple[BrowserResult, ...]:
        """Execute a batch sequence of browser actions sequentially.

        Args:
            session_id: Target session identifier UUID.
            batch: BrowserBatch command containing action sequence.

        Returns:
            tuple[BrowserResult, ...]: Tuple of execution results for each action.

        Raises:
            BatchExecutionError: If any action in the sequence fails or is cancelled.
        """
        results: list[BrowserResult] = []

        for action in batch.actions:
            if session_id in self._cancelled_sessions:
                cancelled_res = self._build_result(
                    action_id=action.action_id,
                    success=False,
                    status=BrowserExecutionStatus.CANCELLED,
                    error=f"Batch execution cancelled for session {session_id}.",
                )
                results.append(cancelled_res)
                raise BatchExecutionError(
                    f"Batch {batch.batch_id} cancelled during action {action.action_id}."
                )

            try:
                res = await self.execute_action(session_id, action)
                results.append(res)
                if not res.success:
                    raise BatchExecutionError(
                        f"Action {action.action_id} ({action.action_type}) failed: {res.error}"
                    )
            except ActionExecutionError as e:
                failed_res = self._build_result(
                    action_id=action.action_id,
                    success=False,
                    status=BrowserExecutionStatus.FAILED,
                    error=str(e),
                )
                results.append(failed_res)
                raise BatchExecutionError(
                    f"Batch {batch.batch_id} failed during action {action.action_id}: {str(e)}"
                ) from e

        return tuple(results)

    async def _dispatch_action(
        self,
        session_id: UUID,
        action: BrowserAction,
        handle: BrowserRuntimeHandle,
    ) -> BrowserResult:
        """Internal helper to dispatch an action to its corresponding handler.

        Args:
            session_id: Session identifier UUID.
            action: BrowserAction command.
            handle: Public BrowserRuntimeHandle instance.

        Returns:
            BrowserResult: Execution outcome result.

        Raises:
            ActionExecutionError: If action type is unsupported or handler execution fails.
        """
        handler = self._handlers.get(action.action_type)
        if not handler:
            raise ActionExecutionError(
                f"Unsupported browser action type: '{action.action_type}'."
            )

        try:
            return await handler(session_id, action, handle)
        except ActionExecutionError:
            raise
        except Exception as e:
            raise ActionExecutionError(
                f"Action {action.action_id} ({action.action_type}) failed: {str(e)}"
            ) from e

    def _build_result(
        self,
        action_id: UUID,
        success: bool,
        status: BrowserExecutionStatus,
        url: str | None = None,
        title: str | None = None,
        value: str | None = None,
        screenshot_base64: str | None = None,
        error: str | None = None,
        duration_ms: float = 0.0,
    ) -> BrowserResult:
        """Internal helper to construct an immutable BrowserResult.

        Args:
            action_id: Associated action identifier UUID.
            success: Boolean success flag.
            status: BrowserExecutionStatus enum value.
            url: Active page URL after action.
            title: Active document title after action.
            value: Extracted value string if applicable.
            screenshot_base64: Screenshot image data if applicable.
            error: Diagnostic error message.
            duration_ms: Total duration in milliseconds.

        Returns:
            BrowserResult: Immutable result instance.
        """
        return BrowserResult(
            action_id=action_id,
            success=success,
            status=status,
            url=url,
            title=title,
            value=value,
            screenshot_base64=screenshot_base64,
            error=error,
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Reusable Helper Placeholders
    # ------------------------------------------------------------------

    def _navigation_placeholder(
        self, action: BrowserAction, url: str | None = None
    ) -> BrowserResult:
        return self._build_result(
            action.action_id,
            success=True,
            status=BrowserExecutionStatus.SUCCESS,
            url=url or action.url,
        )

    def _input_placeholder(
        self, action: BrowserAction, value: str | None = None
    ) -> BrowserResult:
        return self._build_result(
            action.action_id,
            success=True,
            status=BrowserExecutionStatus.SUCCESS,
            value=value or action.value,
        )

    def _element_placeholder(self, action: BrowserAction) -> BrowserResult:
        return self._build_result(
            action.action_id,
            success=True,
            status=BrowserExecutionStatus.SUCCESS,
        )

    def _extraction_placeholder(
        self, action: BrowserAction, value: str | None = None
    ) -> BrowserResult:
        return self._build_result(
            action.action_id,
            success=True,
            status=BrowserExecutionStatus.SUCCESS,
            value=value,
        )

    # ------------------------------------------------------------------
    # Action Handlers Delegating to Placeholders
    # ------------------------------------------------------------------

    async def _execute_goto(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._navigation_placeholder(action, url=action.url)

    async def _execute_click(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_double_click(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_right_click(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_type(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_fill(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_clear(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_select(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_select_option(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_check(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_uncheck(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_hover(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_scroll(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_press(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_press_key(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_focus(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_blur(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_drag(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_drop(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_upload(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._input_placeholder(action)

    async def _execute_download(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_wait(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_wait_for_element(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_wait_for_url(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._navigation_placeholder(action, url=action.url)

    async def _execute_wait_for_network_idle(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_extract_text(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        extracted = (
            action.element.text if (action.element and action.element.text) else action.value
        )
        return self._extraction_placeholder(action, value=extracted)

    async def _execute_extract_attribute(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        attr_val = None
        if action.element and action.value:
            attr_val = action.element.attributes.get(action.value)
        return self._extraction_placeholder(action, value=attr_val)

    async def _execute_screenshot(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._build_result(
            action.action_id,
            success=True,
            status=BrowserExecutionStatus.SUCCESS,
            screenshot_base64="",
        )

    async def _execute_close(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_back(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_forward(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)

    async def _execute_reload(
        self, session_id: UUID, action: BrowserAction, handle: BrowserRuntimeHandle
    ) -> BrowserResult:
        return self._element_placeholder(action)
