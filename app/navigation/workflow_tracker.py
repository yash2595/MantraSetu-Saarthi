"""Workflow Memory & Progress Continuation Tracker for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.navigation.state_store import NavigationStateStore

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    """Active multi-prompt workflow state model."""

    workflow_id: str
    workflow_name: str
    current_step: str
    step_index: int = 0
    total_steps: int = 1
    workflow_data: dict[str, Any] = field(default_factory=dict)
    is_completed: bool = False
    is_cancelled: bool = False
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "current_step": self.current_step,
            "step_index": self.step_index,
            "total_steps": self.total_steps,
            "workflow_data": dict(self.workflow_data),
            "is_completed": self.is_completed,
            "is_cancelled": self.is_cancelled,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


class WorkflowTracker:
    """Manager maintaining workflow progress across voice prompts, disconnects, and navigations."""

    def __init__(self, state_store: NavigationStateStore | None = None) -> None:
        self._store = state_store or NavigationStateStore()
        self._active_workflows: dict[str, WorkflowContext] = {}
        self._lock = Lock()

    def start_workflow(
        self,
        session_id: str,
        workflow_name: str,
        initial_step: str = "INIT",
        total_steps: int = 3,
        initial_data: dict[str, Any] | None = None,
    ) -> WorkflowContext:
        """Start a new workflow for a session."""
        with self._lock:
            ctx = WorkflowContext(
                workflow_id=f"wf_{session_id}_{int(datetime.now().timestamp())}",
                workflow_name=workflow_name,
                current_step=initial_step,
                step_index=0,
                total_steps=total_steps,
                workflow_data=initial_data or {},
            )
            self._active_workflows[session_id] = ctx
            self._store.update_workflow(session_id, workflow_name, initial_step)
            logger.info("Workflow '%s' started for session '%s'", workflow_name, session_id)
            return ctx

    def advance_step(
        self,
        session_id: str,
        next_step: str,
        step_data: dict[str, Any] | None = None,
    ) -> WorkflowContext | None:
        """Advance active workflow step and merge step payload data."""
        with self._lock:
            ctx = self._active_workflows.get(session_id)
            if not ctx or ctx.is_completed or ctx.is_cancelled:
                logger.warning("Cannot advance workflow: No active workflow found for session '%s'", session_id)
                return None

            ctx.current_step = next_step
            ctx.step_index += 1
            if step_data:
                ctx.workflow_data.update(step_data)

            if ctx.step_index >= ctx.total_steps:
                ctx.is_completed = True

            ctx.updated_at = datetime.now(timezone.utc).isoformat()
            self._store.update_workflow(session_id, ctx.workflow_name, next_step)
            logger.info("Workflow '%s' advanced to step '%s' [%d/%d]", ctx.workflow_name, next_step, ctx.step_index, ctx.total_steps)
            return ctx

    def get_active_workflow(self, session_id: str) -> WorkflowContext | None:
        """Get current active workflow for session."""
        with self._lock:
            return self._active_workflows.get(session_id)

    def cancel_workflow(self, session_id: str) -> None:
        """Cancel active workflow for session."""
        with self._lock:
            ctx = self._active_workflows.get(session_id)
            if ctx:
                ctx.is_cancelled = True
                self._store.update_workflow(session_id, None, None)
                self._active_workflows.pop(session_id, None)
                logger.info("Workflow '%s' cancelled for session '%s'", ctx.workflow_name, session_id)
