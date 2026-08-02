"""Dynamic Navigation Context Builder for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager, ConversationMemorySnapshot
from app.navigation.registry import RouteRegistry
from app.navigation.state_store import NavigationStateStore, NavigationSessionState
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_tracker import WorkflowTracker

logger = logging.getLogger(__name__)


@dataclass
class AINavigationContext:
    """Complete immutable navigation context snapshot injected into AI & reasoning engines."""

    session_id: str
    conversation_id: str
    current_page: str
    previous_page: str | None
    navigation_history: list[str]
    current_route_parameters: dict[str, Any]
    pending_navigation: str | None
    pending_action: str | None
    active_workflow: str | None
    workflow_step: str | None
    auth_state: str
    last_user_intent: str | None
    visited_pages: list[str]
    recent_navigation_stack: list[str]
    breadcrumb_trail: list[str]
    supported_ai_actions: list[str]
    page_metadata: dict[str, Any] = field(default_factory=dict)
    ui_elements: list[dict[str, Any]] = field(default_factory=list)
    memory_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context snapshot into serializable dictionary."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "current_page": self.current_page,
            "previous_page": self.previous_page,
            "navigation_history": list(self.navigation_history),
            "current_route_parameters": dict(self.current_route_parameters),
            "pending_navigation": self.pending_navigation,
            "pending_action": self.pending_action,
            "active_workflow": self.active_workflow,
            "workflow_step": self.workflow_step,
            "auth_state": self.auth_state,
            "last_user_intent": self.last_user_intent,
            "visited_pages": list(self.visited_pages),
            "recent_navigation_stack": list(self.recent_navigation_stack),
            "breadcrumb_trail": list(self.breadcrumb_trail),
            "supported_ai_actions": list(self.supported_ai_actions),
            "page_metadata": dict(self.page_metadata),
            "ui_elements": list(self.ui_elements),
            "memory_summary": dict(self.memory_summary),
        }


class NavigationContextBuilder:
    """Builder generating dynamic navigation context snapshots from 5 foundation stores without owning state."""

    def __init__(
        self,
        state_store: NavigationStateStore | None = None,
        registry: RouteRegistry | None = None,
        workflow_tracker: WorkflowTracker | None = None,
        memory_manager: ConversationMemoryManager | None = None,
        ui_registry: UIRegistry | None = None,
        context_cache: ContextCache | None = None,
    ) -> None:
        self._state_store = state_store or NavigationStateStore()
        self._registry = registry or RouteRegistry()
        self._workflow_tracker = workflow_tracker or WorkflowTracker(self._state_store)
        self._memory_manager = memory_manager or ConversationMemoryManager()
        self._ui_registry = ui_registry or UIRegistry()
        self._context_cache = context_cache or ContextCache(version="4.1")
        self._lock = threading.RLock()

    def build_context(self, session_id: str, conversation_id: str = "") -> AINavigationContext:
        """Dynamically assemble runtime AINavigationContext snapshot using all 5 foundation sources."""
        with self._lock:
            # 1. Fetch Session State from NavigationStateStore
            session_state: NavigationSessionState = self._state_store.get_state(session_id)
            current_page = session_state.current_page or "/"

            # 2. Check Static Route Metadata from RouteRegistry / ContextCache
            cache_key = f"route_meta:{current_page}"
            page_meta = self._context_cache.get(cache_key)
            if page_meta is None:
                current_node = self._registry.match_path(current_page)
                page_meta = dict(current_node.metadata) if current_node and current_node.metadata else {}
                self._context_cache.set(cache_key, page_meta)

            breadcrumb = page_meta.get("breadcrumb", [current_page])
            actions = page_meta.get("supported_ai_actions", ["NAVIGATE"])

            # 3. Active Workflow Resolution
            wf = self._workflow_tracker.get_active_workflow(session_id)
            if wf and not wf.is_completed and not wf.is_cancelled:
                active_wf_name = wf.workflow_name
                active_wf_step = wf.current_step
            else:
                active_wf_name = session_state.active_workflow
                active_wf_step = session_state.workflow_step

            # 4. Fetch Conversational Memory from ConversationMemoryManager
            conv_id = conversation_id or session_state.conversation_id or session_id
            memory_snap: ConversationMemorySnapshot = self._memory_manager.get_memory(session_id)
            memory_summary = {
                "user_goals": list(memory_snap.user_goals),
                "extracted_entities": dict(memory_snap.extracted_entities),
                "confirmed_inputs": dict(memory_snap.confirmed_inputs),
                "pending_inputs": list(memory_snap.pending_inputs),
                "intent_history": list(memory_snap.intent_history[-5:]),
            }

            # 5. Fetch UI Components for Route from UIRegistry
            ui_elems_raw = self._ui_registry.get_elements_by_page(current_page)
            ui_elements = [
                {
                    "element_id": elem.element_id,
                    "component_type": str(elem.component_type),
                    "label": elem.semantic_label,
                    "is_visible": elem.is_visible,
                    "is_enabled": elem.is_enabled,
                }
                for elem in ui_elems_raw
            ]

            context = AINavigationContext(
                session_id=session_id,
                conversation_id=conv_id,
                current_page=current_page,
                previous_page=session_state.previous_page,
                navigation_history=list(session_state.navigation_history),
                current_route_parameters=dict(session_state.current_route_parameters),
                pending_navigation=session_state.pending_navigation,
                pending_action=session_state.pending_action,
                active_workflow=active_wf_name,
                workflow_step=active_wf_step,
                auth_state=str(session_state.auth_state),
                last_user_intent=session_state.last_user_intent,
                visited_pages=list(session_state.visited_pages),
                recent_navigation_stack=session_state.navigation_history[-5:],
                breadcrumb_trail=list(breadcrumb),
                supported_ai_actions=list(actions),
                page_metadata=dict(page_meta),
                ui_elements=ui_elements,
                memory_summary=memory_summary,
            )

            logger.debug("Built dynamic AINavigationContext snapshot for session '%s'", session_id)
            return context
