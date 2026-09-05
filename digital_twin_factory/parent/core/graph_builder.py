"""
GraphBuilder: in-memory manager for the TwinModel graph.
Wraps NetworkX operations and exposes a clean API to the UI layer.
"""
from __future__ import annotations

import uuid
from typing import Optional

import networkx as nx

from ...shared_logic.models import (
    GraphEdge,
    GraphNode,
    NodeType,
    SaaSProvider,
    SLARule,
    TwinModel,
)
from ...shared_logic.graph_schema import twin_to_networkx, twin_to_dict, twin_from_dict


class GraphBuilder:
    """Maintains and mutates the current TwinModel."""

    def __init__(self, model: Optional[TwinModel] = None) -> None:
        self.model: TwinModel = model or TwinModel()
        self._nx: nx.DiGraph = twin_to_networkx(self.model)

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def add_node(
        self,
        label: str,
        node_type: NodeType = NodeType.HUMAN,
        description: str = "",
        saas_provider: Optional[SaaSProvider] = None,
        saas_module_id: str = "",
        sla: Optional[SLARule] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> GraphNode:
        node = GraphNode(
            id=str(uuid.uuid4()),
            label=label,
            node_type=node_type,
            description=description,
            saas_provider=saas_provider,
            saas_module_id=saas_module_id,
            sla=sla,
            position_x=position_x,
            position_y=position_y,
        )
        self.model.nodes.append(node)
        self._nx.add_node(node.id, label=label, node_type=node_type.value)
        return node

    def remove_node(self, node_id: str) -> None:
        self.model.nodes = [n for n in self.model.nodes if n.id != node_id]
        self.model.edges = [
            e for e in self.model.edges if e.source_id != node_id and e.target_id != node_id
        ]
        if node_id in self._nx:
            self._nx.remove_node(node_id)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return next((n for n in self.model.nodes if n.id == node_id), None)

    def update_node(self, node_id: str, **kwargs) -> None:
        node = self.get_node(node_id)
        if not node:
            return
        for key, value in kwargs.items():
            if hasattr(node, key):
                setattr(node, key, value)
        # Sync nx attributes
        if node_id in self._nx:
            self._nx.nodes[node_id].update(kwargs)

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        label: str = "",
        condition: str = "",
    ) -> Optional[GraphEdge]:
        if not self.get_node(source_id) or not self.get_node(target_id):
            return None
        edge = GraphEdge(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            label=label,
            condition=condition,
        )
        self.model.edges.append(edge)
        self._nx.add_edge(source_id, target_id, id=edge.id, label=label)
        return edge

    def remove_edge(self, edge_id: str) -> None:
        edge = next((e for e in self.model.edges if e.id == edge_id), None)
        if not edge:
            return
        self.model.edges.remove(edge)
        if self._nx.has_edge(edge.source_id, edge.target_id):
            self._nx.remove_edge(edge.source_id, edge.target_id)

    # ------------------------------------------------------------------
    # SaaS mapping
    # ------------------------------------------------------------------

    def map_node_to_saas(self, node_id: str, provider: SaaSProvider, module_id: str) -> None:
        self.update_node(node_id, saas_provider=provider, saas_module_id=module_id, node_type=NodeType.AUTOMATED)

    # ------------------------------------------------------------------
    # Analysis helpers
    # ------------------------------------------------------------------

    def get_critical_path(self) -> list[str]:
        """Return node IDs on the longest path (by SLA duration)."""
        try:
            def weight(u, v, _data):
                node = self.get_node(u)
                return -(node.sla.max_duration_seconds if node and node.sla else 60)

            path = nx.dag_longest_path(self._nx, weight=weight)
            return path
        except Exception:
            return []

    def total_theoretical_duration(self, exclude_node_ids: Optional[list[str]] = None) -> float:
        """Sum of SLA max durations along the longest path."""
        exclude = set(exclude_node_ids or [])
        total = 0.0
        for node in self.model.nodes:
            if node.id not in exclude and node.sla:
                total += node.sla.max_duration_seconds
        return total

    def rebuild_nx(self) -> None:
        self._nx = twin_to_networkx(self.model)

    def to_dict(self) -> dict:
        return twin_to_dict(self.model)
