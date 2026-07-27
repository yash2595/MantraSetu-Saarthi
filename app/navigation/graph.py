"""In-memory website structure graph implementation for MantraSetu AgentOS.

This module implements NavigationGraph using BFS pathfinding algorithm and thread-safe asyncio primitives
for storing nodes and edges representing website navigation structure without external database dependencies.
"""

from __future__ import annotations

import asyncio
from collections import deque
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    BaseNavigationGraph,
    NavigationGraphError,
    NavigationInitializationError,
)
from app.navigation.models import NavigationEdge, WebsiteNode


class NavigationGraph(BaseNavigationGraph):
    """Thread-safe in-memory navigation graph implementing BaseNavigationGraph.

    Responsibility:
        Maintains nodes (pages/forms) and directed edges (transition actions) representing website structure,
        supporting BFS-based optimal path calculation between site nodes without browser SDKs or databases.
    """

    def __init__(self) -> None:
        """Initialize NavigationGraph with internal node/edge registries and asyncio lock."""
        self._nodes: dict[UUID, WebsiteNode] = {}
        self._edges: dict[UUID, tuple[NavigationEdge, ...]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the navigation graph has been initialized.

        Raises:
            NavigationInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise NavigationInitializationError(
                "NavigationGraph is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize navigation graph runtime state. Idempotent."""
        async with self._lock:
            if self._initialized:
                return
            self._initialized = True

    async def close(self) -> None:
        """Close navigation graph and clear all registered nodes and edges."""
        async with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._initialized = False

    async def add_node(self, node: WebsiteNode) -> None:
        """Add a WebsiteNode to the in-memory graph.

        Args:
            node: WebsiteNode instance to register.

        Raises:
            NavigationInitializationError: If graph is uninitialized.
            NavigationGraphError: If node parameter is invalid.
        """
        self._require_initialized()
        if not isinstance(node, WebsiteNode):
            raise NavigationGraphError("Invalid WebsiteNode instance provided.")

        async with self._lock:
            self._nodes[node.node_id] = node
            if node.node_id not in self._edges:
                self._edges[node.node_id] = ()

    async def add_edge(self, edge: NavigationEdge) -> None:
        """Add a directed NavigationEdge transition connecting two registered nodes.

        Args:
            edge: NavigationEdge instance to register.

        Raises:
            NavigationInitializationError: If graph is uninitialized.
            NavigationGraphError: If source or target node is not registered in graph.
        """
        self._require_initialized()
        if not isinstance(edge, NavigationEdge):
            raise NavigationGraphError("Invalid NavigationEdge instance provided.")

        async with self._lock:
            if edge.source_node_id not in self._nodes:
                raise NavigationGraphError(
                    f"Source node '{edge.source_node_id}' is not registered in navigation graph."
                )
            if edge.target_node_id not in self._nodes:
                raise NavigationGraphError(
                    f"Target node '{edge.target_node_id}' is not registered in navigation graph."
                )

            existing_edges = self._edges.get(edge.source_node_id, ())
            self._edges[edge.source_node_id] = existing_edges + (edge,)

    async def find_path(
        self,
        source: UUID,
        target: UUID,
    ) -> tuple[WebsiteNode, ...]:
        """Find optimal path sequence of WebsiteNode entities using Breadth-First Search (BFS).

        Args:
            source: Source node identifier UUID.
            target: Target node identifier UUID.

        Returns:
            tuple[WebsiteNode, ...]: Immutable tuple of ordered WebsiteNode entities along path.

        Raises:
            NavigationInitializationError: If graph is uninitialized.
            NavigationGraphError: If source/target node is not found or no path exists.
        """
        self._require_initialized()
        if not isinstance(source, UUID) or not isinstance(target, UUID):
            raise NavigationGraphError("Source and target identifiers must be valid UUIDs.")

        async with self._lock:
            if source not in self._nodes:
                raise NavigationGraphError(f"Source node '{source}' not found in graph.")
            if target not in self._nodes:
                raise NavigationGraphError(f"Target node '{target}' not found in graph.")

            if source == target:
                return (self._nodes[source],)

            # BFS traversal
            queue: deque[list[UUID]] = deque([[source]])
            visited: set[UUID] = {source}

            while queue:
                current_path = queue.popleft()
                curr_node_id = current_path[-1]

                for edge in self._edges.get(curr_node_id, ()):
                    next_node_id = edge.target_node_id
                    if next_node_id == target:
                        full_node_ids = current_path + [next_node_id]
                        return tuple(self._nodes[nid] for nid in full_node_ids)

                    if next_node_id not in visited:
                        visited.add(next_node_id)
                        queue.append(current_path + [next_node_id])

            raise NavigationGraphError(
                f"No navigation path exists between source node '{source}' and target node '{target}'."
            )

    async def clear(self) -> None:
        """Purge all nodes and edges from memory.

        Raises:
            NavigationInitializationError: If graph is uninitialized.
        """
        self._require_initialized()
        async with self._lock:
            self._nodes.clear()
            self._edges.clear()

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the navigation graph.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        return ComponentHealth(
            component_name="navigation_graph",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="NavigationGraph operational."
            if self._initialized
            else "NavigationGraph uninitialized.",
        )
