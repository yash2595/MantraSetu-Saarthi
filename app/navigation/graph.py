"""In-memory Navigation Graph domain component for MantraSetu AgentOS.

This module provides the canonical directed graph representation of application routes,
UI states, and valid transition edges for the Navigation Intelligence system.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any
from uuid import UUID

from app.navigation.models import NavigationAction, NavigationActionType, NavigationEdge, NavigationNode


class NavigationGraph:
    """In-memory directed graph managing navigation nodes and transition edges.

    Responsibility:
        Maintains vertices (NavigationNode) and directed edges (NavigationEdge) with
        bidirectional adjacency lists, as well as constant-time O(1) edge indices
        (_edge_lookup and _logical_edges), enabling rapid topological queries, O(1) edge
        lookups, and instant graph integrity validation.
    """

    def __init__(self) -> None:
        """Initialize an empty NavigationGraph."""
        self._nodes: dict[UUID, NavigationNode] = {}
        self._edges: dict[UUID, NavigationEdge] = {}
        self._adjacency: dict[UUID, set[UUID]] = {}
        self._reverse_adjacency: dict[UUID, set[UUID]] = {}
        self._edge_lookup: dict[tuple[UUID, UUID], NavigationEdge] = {}
        self._logical_edges: set[tuple[UUID, UUID, NavigationActionType]] = set()

    @property
    def nodes(self) -> Mapping[UUID, NavigationNode]:
        """Read-only view of all nodes indexed by node_id.

        Returns:
            Mapping[UUID, NavigationNode]: Immutable proxy view of nodes.
        """
        return MappingProxyType(self._nodes)

    @property
    def edges(self) -> Mapping[UUID, NavigationEdge]:
        """Read-only view of all edges indexed by edge_id.

        Returns:
            Mapping[UUID, NavigationEdge]: Immutable proxy view of edges.
        """
        return MappingProxyType(self._edges)

    def add_node(self, node: NavigationNode) -> None:
        """Add a navigation node to the graph.

        Args:
            node: NavigationNode instance to add.

        Raises:
            ValueError: If a node with the same node_id already exists.
        """
        if node.node_id in self._nodes:
            raise ValueError(f"Node with id {node.node_id} already exists in the graph.")

        self._nodes[node.node_id] = node
        if node.node_id not in self._adjacency:
            self._adjacency[node.node_id] = set()
        if node.node_id not in self._reverse_adjacency:
            self._reverse_adjacency[node.node_id] = set()

    def remove_node(self, node_id: UUID) -> None:
        """Remove a navigation node and all connected edges from the graph.

        Args:
            node_id: Identifier of the node to remove.

        Raises:
            KeyError: If the node_id does not exist in the graph.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node with id {node_id} does not exist in the graph.")

        edges_to_remove = [
            edge_id
            for edge_id, edge in self._edges.items()
            if edge.source_node_id == node_id or edge.destination_node_id == node_id
        ]
        for edge_id in edges_to_remove:
            self.remove_edge(edge_id)

        del self._nodes[node_id]
        self._adjacency.pop(node_id, None)
        self._reverse_adjacency.pop(node_id, None)

    def get_node(self, node_id: UUID) -> NavigationNode | None:
        """Retrieve a navigation node by its unique identifier.

        Args:
            node_id: Identifier of the node to retrieve.

        Returns:
            NavigationNode | None: The matching node instance, or None if not found.
        """
        return self._nodes.get(node_id)

    def has_node(self, node_id: UUID) -> bool:
        """Check if a node exists in the graph.

        Args:
            node_id: Identifier of the node to check.

        Returns:
            bool: True if the node exists, False otherwise.
        """
        return node_id in self._nodes

    def add_edge(self, edge: NavigationEdge) -> None:
        """Add a directed navigation edge between two existing nodes in the graph.

        Args:
            edge: NavigationEdge instance to add.

        Raises:
            ValueError: If an edge with edge_id exists, source/destination nodes do not exist,
                or a duplicate logical edge transition already exists.
        """
        if edge.edge_id in self._edges:
            raise ValueError(f"Edge with id {edge.edge_id} already exists in the graph.")
        if edge.source_node_id not in self._nodes:
            raise ValueError(
                f"Source node id {edge.source_node_id} does not exist in the graph."
            )
        if edge.destination_node_id not in self._nodes:
            raise ValueError(
                f"Destination node id {edge.destination_node_id} does not exist in the graph."
            )

        logical_key = (
            edge.source_node_id,
            edge.destination_node_id,
            edge.action.action_type,
        )
        if logical_key in self._logical_edges:
            raise ValueError(
                f"Duplicate logical edge transition from {edge.source_node_id} "
                f"to {edge.destination_node_id} with action {edge.action.action_type} already exists."
            )

        self._edges[edge.edge_id] = edge
        self._edge_lookup[(edge.source_node_id, edge.destination_node_id)] = edge
        self._logical_edges.add(logical_key)
        self._adjacency[edge.source_node_id].add(edge.destination_node_id)
        self._reverse_adjacency[edge.destination_node_id].add(edge.source_node_id)

    def remove_edge(self, edge_id: UUID) -> None:
        """Remove a navigation edge from the graph.

        Args:
            edge_id: Identifier of the edge to remove.

        Raises:
            KeyError: If the edge_id does not exist in the graph.
        """
        if edge_id not in self._edges:
            raise KeyError(f"Edge with id {edge_id} does not exist in the graph.")

        edge = self._edges.pop(edge_id)
        src = edge.source_node_id
        dst = edge.destination_node_id
        logical_key = (src, dst, edge.action.action_type)

        self._edge_lookup.pop((src, dst), None)
        self._logical_edges.discard(logical_key)

        has_other_out = any(
            (src, dst) == (e.source_node_id, e.destination_node_id)
            for e in self._edges.values()
        )
        if not has_other_out:
            if src in self._adjacency:
                self._adjacency[src].discard(dst)
            if dst in self._reverse_adjacency:
                self._reverse_adjacency[dst].discard(src)

    def get_edge(self, edge_id: UUID) -> NavigationEdge | None:
        """Retrieve a navigation edge by its unique identifier.

        Args:
            edge_id: Identifier of the edge to retrieve.

        Returns:
            NavigationEdge | None: The matching edge instance, or None if not found.
        """
        return self._edges.get(edge_id)

    def get_edge_between(
        self,
        source_node_id: UUID,
        destination_node_id: UUID,
    ) -> NavigationEdge | None:
        """Retrieve the navigation edge connecting a source node to a destination node in O(1) time, if present.

        Args:
            source_node_id: Identifier of the source node.
            destination_node_id: Identifier of the destination node.

        Returns:
            NavigationEdge | None: The matching edge instance, or None if no edge connects the nodes.
        """
        return self._edge_lookup.get((source_node_id, destination_node_id))

    def get_outgoing_edges(self, node_id: UUID) -> tuple[NavigationEdge, ...]:
        """Retrieve all outgoing edges originating from a given node.

        Args:
            node_id: Identifier of the source node.

        Returns:
            tuple[NavigationEdge, ...]: Outgoing edge instances.
        """
        if node_id not in self._nodes:
            return ()
        targets = self._adjacency.get(node_id, set())
        return tuple(
            edge
            for edge in self._edges.values()
            if edge.source_node_id == node_id and edge.destination_node_id in targets
        )

    def get_outgoing_actions(self, node_id: UUID) -> tuple[NavigationAction, ...]:
        """Retrieve all outgoing actions originating from a given node.

        Args:
            node_id: Identifier of the source node.

        Returns:
            tuple[NavigationAction, ...]: Outgoing action instances.
        """
        if node_id not in self._nodes:
            return ()
        return tuple(
            edge.action
            for edge in self._edges.values()
            if edge.source_node_id == node_id
        )

    def has_edge(self, edge_id: UUID) -> bool:
        """Check if an edge exists in the graph.

        Args:
            edge_id: Identifier of the edge to check.

        Returns:
            bool: True if the edge exists, False otherwise.
        """
        return edge_id in self._edges

    def outgoing_neighbors(self, node_id: UUID) -> tuple[NavigationNode, ...]:
        """Retrieve all nodes directly reachable via outgoing edges from the given node.

        Args:
            node_id: Identifier of the source node.

        Returns:
            tuple[NavigationNode, ...]: Tuple of outgoing neighbor node instances.

        Raises:
            KeyError: If the node_id does not exist in the graph.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node with id {node_id} does not exist in the graph.")
        return tuple(
            self._nodes[target_id]
            for target_id in self._adjacency.get(node_id, set())
        )

    def incoming_neighbors(self, node_id: UUID) -> tuple[NavigationNode, ...]:
        """Retrieve all nodes that have directed edges pointing to the given node.

        Args:
            node_id: Identifier of the destination node.

        Returns:
            tuple[NavigationNode, ...]: Tuple of incoming neighbor node instances.

        Raises:
            KeyError: If the node_id does not exist in the graph.
        """
        if node_id not in self._nodes:
            raise KeyError(f"Node with id {node_id} does not exist in the graph.")
        return tuple(
            self._nodes[src_id]
            for src_id in self._reverse_adjacency.get(node_id, set())
        )

    def neighbors(self, node_id: UUID) -> tuple[NavigationNode, ...]:
        """Retrieve all outgoing neighbor nodes for a given node.

        Args:
            node_id: Identifier of the node.

        Returns:
            tuple[NavigationNode, ...]: Tuple of outgoing neighbor node instances.
        """
        return self.outgoing_neighbors(node_id)

    def node_count(self) -> int:
        """Return the total number of nodes in the graph.

        Returns:
            int: Node count.
        """
        return len(self._nodes)

    def edge_count(self) -> int:
        """Return the total number of edges in the graph.

        Returns:
            int: Edge count.
        """
        return len(self._edges)

    def is_empty(self) -> bool:
        """Check whether the navigation graph contains no nodes.

        Returns:
            bool: True if graph contains no nodes, False otherwise.
        """
        return not self._nodes

    def clear(self) -> None:
        """Clear all nodes, edges, adjacency lists, and lookup indices from the graph."""
        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._edge_lookup.clear()
        self._logical_edges.clear()

    def validate_graph(self) -> list[str]:
        """Validate topological integrity and consistency of the navigation graph.

        Checks for missing node references, invalid edge endpoints, isolated nodes,
        duplicate logical transitions, and adjacency list drift.

        Returns:
            list[str]: A list of validation error descriptions. Empty list if graph is valid.
        """
        errors: list[str] = []
        seen_logical_transitions: set[tuple[UUID, UUID, str]] = set()

        for edge_id, edge in self._edges.items():
            if edge.source_node_id not in self._nodes:
                errors.append(
                    f"Edge {edge_id} references missing source node {edge.source_node_id}."
                )
            if edge.destination_node_id not in self._nodes:
                errors.append(
                    f"Edge {edge_id} references missing destination node {edge.destination_node_id}."
                )

            key = (edge.source_node_id, edge.destination_node_id, str(edge.action.action_type))
            if key in seen_logical_transitions:
                errors.append(
                    f"Duplicate logical edge transition detected from {edge.source_node_id} "
                    f"to {edge.destination_node_id} with action {edge.action.action_type}."
                )
            else:
                seen_logical_transitions.add(key)

        for node_id in self._nodes:
            out_degree = len(self._adjacency.get(node_id, set()))
            in_degree = len(self._reverse_adjacency.get(node_id, set()))
            if out_degree == 0 and in_degree == 0:
                errors.append(f"Isolated node detected with id {node_id}.")

        for src_id, targets in self._adjacency.items():
            if src_id not in self._nodes:
                errors.append(
                    f"Adjacency list references missing source node {src_id}."
                )
            for target_id in targets:
                if target_id not in self._nodes:
                    errors.append(
                        f"Adjacency list for node {src_id} references missing target node {target_id}."
                    )

        for dst_id, sources in self._reverse_adjacency.items():
            if dst_id not in self._nodes:
                errors.append(
                    f"Reverse adjacency list references missing destination node {dst_id}."
                )
            for src_id in sources:
                if src_id not in self._nodes:
                    errors.append(
                        f"Reverse adjacency list for node {dst_id} references missing source node {src_id}."
                    )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Serialize the graph topology, nodes, and edges into a dictionary payload.

        Returns:
            dict[str, Any]: Serialized dictionary payload.
        """
        return {
            "nodes": [node.model_dump(mode="json") for node in self._nodes.values()],
            "edges": [edge.model_dump(mode="json") for edge in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NavigationGraph:
        """Deserialize a dictionary payload into a new NavigationGraph instance.

        Args:
            data: Serialized graph dictionary payload containing 'nodes' and 'edges'.

        Returns:
            NavigationGraph: Reconstructed graph instance.
        """
        graph = cls()
        nodes_data = data.get("nodes", [])
        edges_data = data.get("edges", [])

        for node_raw in nodes_data:
            node = NavigationNode.model_validate(node_raw)
            graph.add_node(node)

        for edge_raw in edges_data:
            edge = NavigationEdge.model_validate(edge_raw)
            graph.add_edge(edge)

        return graph
