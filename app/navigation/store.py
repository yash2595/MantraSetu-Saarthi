"""Storage abstractions and in-memory storage implementation for Navigation Intelligence.

This module provides the BaseNavigationStore abstract contract and the concrete MemoryNavigationStore
for persisting navigation states, histories, and execution plans within MantraSetu AgentOS.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from app.navigation.models import NavigationHistory, NavigationPlan, NavigationState


class BaseNavigationStore(ABC):
    """Abstract storage contract for Navigation session state, history, and plans.

    Responsibility:
        Establishes non-blocking asynchronous persistence methods for saving, retrieving,
        and purging navigation domain entities across session lifecycles.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize navigation store connections, pools, and storage resources."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close navigation store connections and release allocated storage resources."""
        ...

    @abstractmethod
    async def save_state(self, state: NavigationState) -> None:
        """Persist a navigation state instance.

        Args:
            state: The NavigationState instance to store.
        """
        ...

    @abstractmethod
    async def get_state(self, session_id: UUID) -> NavigationState | None:
        """Retrieve the navigation state for a given session.

        Args:
            session_id: Unique identifier of the session.

        Returns:
            NavigationState | None: The active state instance, or None if not found.
        """
        ...

    @abstractmethod
    async def delete_state(self, session_id: UUID) -> None:
        """Delete the navigation state for a given session.

        Args:
            session_id: Unique identifier of the session.
        """
        ...

    @abstractmethod
    async def save_history(self, history: NavigationHistory) -> None:
        """Persist a navigation history record.

        Args:
            history: The NavigationHistory instance to store.
        """
        ...

    @abstractmethod
    async def get_history(self, session_id: UUID) -> NavigationHistory | None:
        """Retrieve the navigation history for a given session.

        Args:
            session_id: Unique identifier of the session.

        Returns:
            NavigationHistory | None: The history record, or None if not found.
        """
        ...

    @abstractmethod
    async def delete_history(self, session_id: UUID) -> None:
        """Delete the navigation history for a given session.

        Args:
            session_id: Unique identifier of the session.
        """
        ...

    @abstractmethod
    async def save_plan(
        self, plan: NavigationPlan, session_id: UUID | None = None
    ) -> None:
        """Persist a navigation plan instance.

        Args:
            plan: The NavigationPlan instance to store.
            session_id: Optional session identifier owning this navigation plan.
        """
        ...

    @abstractmethod
    async def get_plan(self, plan_id: UUID) -> NavigationPlan | None:
        """Retrieve a navigation plan by its plan_id.

        Args:
            plan_id: Unique identifier of the navigation plan.

        Returns:
            NavigationPlan | None: The matching plan instance, or None if not found.
        """
        ...

    @abstractmethod
    async def delete_plan(self, plan_id: UUID) -> None:
        """Delete a navigation plan by its plan_id.

        Args:
            plan_id: Unique identifier of the navigation plan.
        """
        ...

    @abstractmethod
    async def clear_session(self, session_id: UUID) -> None:
        """Purge all navigation artifacts (state, history, and associated plans) for a session.

        Args:
            session_id: Unique identifier of the session to clear.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check store availability and health status.

        Returns:
            bool: True if store is healthy and operational, False otherwise.
        """
        ...


class MemoryNavigationStore(BaseNavigationStore):
    """In-memory implementation of BaseNavigationStore.

    Responsibility:
        Provides rapid O(1) dictionary-backed state, history, and plan persistence
        for testing, local execution, and in-memory runtime sessions.
    """

    def __init__(self) -> None:
        """Initialize an empty MemoryNavigationStore."""
        self._states: dict[UUID, NavigationState] = {}
        self._histories: dict[UUID, NavigationHistory] = {}
        self._plans: dict[UUID, NavigationPlan] = {}
        self._session_plans: dict[UUID, set[UUID]] = {}

    @property
    def states(self) -> Mapping[UUID, NavigationState]:
        """Read-only view of in-memory navigation states.

        Returns:
            Mapping[UUID, NavigationState]: Immutable proxy mapping of active states.
        """
        return MappingProxyType(self._states)

    @property
    def histories(self) -> Mapping[UUID, NavigationHistory]:
        """Read-only view of in-memory navigation histories.

        Returns:
            Mapping[UUID, NavigationHistory]: Immutable proxy mapping of active histories.
        """
        return MappingProxyType(self._histories)

    @property
    def plans(self) -> Mapping[UUID, NavigationPlan]:
        """Read-only view of in-memory navigation plans.

        Returns:
            Mapping[UUID, NavigationPlan]: Immutable proxy mapping of active plans.
        """
        return MappingProxyType(self._plans)

    async def initialize(self) -> None:
        """Initialize in-memory storage resources (no-op)."""
        pass

    async def close(self) -> None:
        """Close in-memory storage resources and release allocations (no-op)."""
        pass

    async def save_state(self, state: NavigationState) -> None:
        """Persist a navigation state in memory.

        Args:
            state: The NavigationState instance to store.
        """
        self._states[state.session_id] = state
        if state.current_plan_id:
            if state.session_id not in self._session_plans:
                self._session_plans[state.session_id] = set()
            self._session_plans[state.session_id].add(state.current_plan_id)

    async def get_state(self, session_id: UUID) -> NavigationState | None:
        """Retrieve the in-memory navigation state for a given session.

        Args:
            session_id: Unique identifier of the session.

        Returns:
            NavigationState | None: Matching state, or None if not present.
        """
        return self._states.get(session_id)

    async def delete_state(self, session_id: UUID) -> None:
        """Delete the in-memory navigation state for a given session.

        Args:
            session_id: Unique identifier of the session.
        """
        self._states.pop(session_id, None)

    async def save_history(self, history: NavigationHistory) -> None:
        """Persist a navigation history record in memory.

        Args:
            history: The NavigationHistory instance to store.
        """
        self._histories[history.session_id] = history

    async def get_history(self, session_id: UUID) -> NavigationHistory | None:
        """Retrieve the in-memory navigation history for a given session.

        Args:
            session_id: Unique identifier of the session.

        Returns:
            NavigationHistory | None: Matching history, or None if not present.
        """
        return self._histories.get(session_id)

    async def delete_history(self, session_id: UUID) -> None:
        """Delete the in-memory navigation history for a given session.

        Args:
            session_id: Unique identifier of the session.
        """
        self._histories.pop(session_id, None)

    async def save_plan(
        self, plan: NavigationPlan, session_id: UUID | None = None
    ) -> None:
        """Persist a navigation plan instance in memory and register under owning session.

        Args:
            plan: The NavigationPlan instance to store.
            session_id: Optional session identifier owning this plan.
        """
        self._plans[plan.plan_id] = plan
        if session_id:
            if session_id not in self._session_plans:
                self._session_plans[session_id] = set()
            self._session_plans[session_id].add(plan.plan_id)

    async def get_plan(self, plan_id: UUID) -> NavigationPlan | None:
        """Retrieve a navigation plan by its plan_id from memory.

        Args:
            plan_id: Unique identifier of the navigation plan.

        Returns:
            NavigationPlan | None: Matching plan, or None if not present.
        """
        return self._plans.get(plan_id)

    async def delete_plan(self, plan_id: UUID) -> None:
        """Delete a navigation plan by its plan_id from memory and session tracking.

        Args:
            plan_id: Unique identifier of the navigation plan.
        """
        self._plans.pop(plan_id, None)
        for plan_set in self._session_plans.values():
            plan_set.discard(plan_id)

    async def clear_session(self, session_id: UUID) -> None:
        """Purge all navigation artifacts (state, history, and associated plans) for a session.

        Args:
            session_id: Unique identifier of the session to clear.
        """
        state = self._states.pop(session_id, None)
        self._histories.pop(session_id, None)

        associated_plan_ids = self._session_plans.pop(session_id, set())
        if state and state.current_plan_id:
            associated_plan_ids.add(state.current_plan_id)

        for plan_id in associated_plan_ids:
            self._plans.pop(plan_id, None)

    async def health_check(self) -> bool:
        """Check in-memory store health.

        Returns:
            bool: Always True for in-memory storage.
        """
        return True
