"""Abstract base contract for the Navigation Engine in MantraSetu AgentOS.

This module defines the abstract interface that all navigation engine implementations
must satisfy, maintaining Clean Architecture, Domain-Driven Design, and Dependency Inversion.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.navigation.models import (
    NavigationHistory,
    NavigationPlan,
    NavigationState,
)


class BaseNavigationEngine(ABC):
    """Abstract interface defining the contract for Navigation Engine implementations.

    Responsibility:
        Establishes the lifecycle, state management, path planning, and resource
        handling operations required across all Navigation Engine components.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize navigation engine resources and runtime dependencies."""
        pass

    @abstractmethod
    async def get_state(self, session_id: UUID) -> NavigationState:
        """Retrieve the active navigation state for a given session.

        Args:
            session_id: Unique identifier of the navigation session.

        Returns:
            NavigationState: The active navigation state associated with the session.
        """
        pass

    @abstractmethod
    async def update_state(self, state: NavigationState) -> None:
        """Persist or update the navigation state for a session.

        Args:
            state: The navigation state instance to persist.
        """
        pass

    @abstractmethod
    async def get_history(self, session_id: UUID) -> NavigationHistory:
        """Retrieve the chronological navigation history log for a session.

        Args:
            session_id: Unique identifier of the navigation session.

        Returns:
            NavigationHistory: Chronological history record for the session.
        """
        pass

    @abstractmethod
    async def can_navigate(
        self,
        source_node_id: UUID,
        target_node_id: UUID,
    ) -> bool:
        """Determine whether a valid navigation path exists between source and target nodes.

        Args:
            source_node_id: Identifier of the originating navigation node.
            target_node_id: Identifier of the destination target node.

        Returns:
            bool: True if navigation is feasible, False otherwise.
        """
        pass

    @abstractmethod
    async def plan_navigation(
        self,
        session_id: UUID,
        target_node_id: UUID,
    ) -> NavigationPlan:
        """Generate an action plan sequence for a session to navigate to a target node.

        Args:
            session_id: Unique identifier of the navigation session.
            target_node_id: Identifier of the destination target node.

        Returns:
            NavigationPlan: Structured plan manifest detailing the actions required.
        """
        pass

    @abstractmethod
    async def reset(self, session_id: UUID) -> None:
        """Reset and clear the navigation state and active plan for a session.

        Args:
            session_id: Unique identifier of the navigation session to reset.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check the health and operational availability of the navigation engine.

        Returns:
            bool: True if the engine and its dependencies are healthy, False otherwise.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Release all allocated engine resources, connections, and background tasks."""
        pass
