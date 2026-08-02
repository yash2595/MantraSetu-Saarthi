"""Real-time Frontend-AI Event Synchronization Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.state_store import NavigationStateStore
from app.navigation.workflow_tracker import WorkflowTracker

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "NavigationSyncManager"
_COMPONENT_VERSION = "4.1"


class NavigationSyncManager:
    """Manager handling real-time frontend lifecycle sync events and state store alignment."""

    def __init__(
        self,
        state_store: NavigationStateStore | None = None,
        workflow_tracker: WorkflowTracker | None = None,
    ) -> None:
        self._state_store = state_store or NavigationStateStore()
        self._workflow_tracker = workflow_tracker or WorkflowTracker(self._state_store)
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._events_processed_count = 0

    def handle_frontend_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle incoming frontend lifecycle sync event and update navigation state store."""
        with self._lock:
            self._events_processed_count += 1
            payload = payload or {}
            event_name = event_type.upper()
            logger.debug("Processing frontend sync event '%s' for session '%s'", event_name, session_id)

            if event_name in ("PAGE_CHANGED", "PAGE_LOADED", "NAVIGATION_COMPLETED", "PAGE_REFRESH", "SESSION_RESTORED"):
                path = payload.get("path", payload.get("url", "/"))
                params = payload.get("parameters", {})
                state = self._state_store.update_current_page(session_id, path, params)
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

            elif event_name == "BROWSER_BACK":
                prev_page = self._state_store.undo(session_id)
                state = self._state_store.get_state(session_id)
                return {"status": "SUCCESS", "event": event_name, "restored_page": prev_page, "state": state.to_dict()}

            elif event_name == "BROWSER_FORWARD":
                state = self._state_store.get_state(session_id)
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

            elif event_name == "WORKFLOW_STARTED":
                wf_name = payload.get("workflow_name", "UNKNOWN_WORKFLOW")
                init_step = payload.get("initial_step", "INIT")
                wf_ctx = self._workflow_tracker.start_workflow(session_id, wf_name, init_step)
                return {"status": "SUCCESS", "event": event_name, "workflow": wf_ctx.to_dict()}

            elif event_name == "WORKFLOW_CANCELLED":
                self._workflow_tracker.cancel_workflow(session_id)
                return {"status": "SUCCESS", "event": event_name}

            elif event_name in ("FORM_UPDATED", "INPUT_CHANGED", "FORM_SUBMITTED"):
                field_name = payload.get("field")
                val = payload.get("value")
                if field_name:
                    state = self._state_store.get_state(session_id)
                    state.current_route_parameters[field_name] = val
                return {"status": "SUCCESS", "event": event_name}

            elif event_name in ("MODAL_OPENED", "MODAL_CLOSED", "USER_CLICK", "API_SUCCESS", "API_FAILED", "OTP_VERIFIED", "FILE_UPLOADED", "NETWORK_LOST", "NETWORK_RESTORED"):
                state = self._state_store.get_state(session_id)
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

            elif event_name in ("LOGIN", "PAYMENT_SUCCESS"):
                state = self._state_store.get_state(session_id)
                state.auth_state = "AUTHENTICATED"
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

            elif event_name in ("LOGOUT", "PAYMENT_FAILED"):
                state = self._state_store.get_state(session_id)
                state.auth_state = "ANONYMOUS"
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

            else:
                state = self._state_store.get_state(session_id)
                return {"status": "SUCCESS", "event": event_name, "state": state.to_dict()}

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_processed_count": self._events_processed_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="NavigationSyncManager operational.",
        )
