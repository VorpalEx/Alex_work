"""JSON serialisation/deserialisation for TwinModel <-> NetworkX graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from .models import (
    GraphEdge,
    GraphNode,
    NodeType,
    SaaSConfig,
    SaaSProvider,
    SLARule,
    StepStatus,
    TwinModel,
    UserRole,
)


def twin_to_networkx(model: TwinModel) -> nx.DiGraph:
    """Convert a TwinModel into a NetworkX directed graph."""
    g: nx.DiGraph = nx.DiGraph()
    for node in model.nodes:
        g.add_node(
            node.id,
            label=node.label,
            node_type=node.node_type.value,
            description=node.description,
            saas_provider=node.saas_provider.value if node.saas_provider else None,
            saas_module_id=node.saas_module_id,
            position_x=node.position_x,
            position_y=node.position_y,
            sla_max=node.sla.max_duration_seconds if node.sla else None,
            sla_warn_pct=node.sla.warning_threshold_pct if node.sla else 0.20,
        )
    for edge in model.edges:
        g.add_edge(edge.source_id, edge.target_id, id=edge.id, label=edge.label, condition=edge.condition)
    return g


def twin_to_dict(model: TwinModel) -> dict[str, Any]:
    """Serialise TwinModel to a plain dict (for config.json injection)."""
    nodes_data = []
    for n in model.nodes:
        nd: dict[str, Any] = {
            "id": n.id,
            "label": n.label,
            "node_type": n.node_type.value,
            "description": n.description,
            "saas_provider": n.saas_provider.value if n.saas_provider else None,
            "saas_module_id": n.saas_module_id,
            "position_x": n.position_x,
            "position_y": n.position_y,
            "status": n.status.value,
            "metadata": n.metadata,
        }
        if n.sla:
            nd["sla"] = {
                "step_id": n.sla.step_id,
                "max_duration_seconds": n.sla.max_duration_seconds,
                "description": n.sla.description,
                "warning_threshold_pct": n.sla.warning_threshold_pct,
            }
        else:
            nd["sla"] = None
        nodes_data.append(nd)

    edges_data = [
        {"id": e.id, "source_id": e.source_id, "target_id": e.target_id, "label": e.label, "condition": e.condition}
        for e in model.edges
    ]

    saas_data: dict[str, Any] = {}
    for provider_key, cfg in model.saas_configs.items():
        saas_data[provider_key] = {
            "provider": cfg.provider.value,
            "api_key": cfg.api_key,
            "webhook_url": cfg.webhook_url,
            "base_url": cfg.base_url,
            "extra_params": cfg.extra_params,
        }

    return {
        "id": model.id,
        "company_name": model.company_name,
        "version": model.version,
        "pdf_source_path": model.pdf_source_path,
        "created_at": model.created_at,
        "description": model.description,
        "nodes": nodes_data,
        "edges": edges_data,
        "saas_configs": saas_data,
    }


def twin_from_dict(data: dict[str, Any]) -> TwinModel:
    """Deserialise a TwinModel from a plain dict (loaded from config.json)."""
    nodes: list[GraphNode] = []
    for nd in data.get("nodes", []):
        sla = None
        if nd.get("sla"):
            s = nd["sla"]
            sla = SLARule(
                step_id=s["step_id"],
                max_duration_seconds=s["max_duration_seconds"],
                description=s["description"],
                warning_threshold_pct=s.get("warning_threshold_pct", 0.20),
            )
        nodes.append(
            GraphNode(
                id=nd["id"],
                label=nd["label"],
                node_type=NodeType(nd["node_type"]),
                description=nd.get("description", ""),
                saas_provider=SaaSProvider(nd["saas_provider"]) if nd.get("saas_provider") else None,
                saas_module_id=nd.get("saas_module_id", ""),
                position_x=nd.get("position_x", 0.0),
                position_y=nd.get("position_y", 0.0),
                status=StepStatus(nd.get("status", "idle")),
                metadata=nd.get("metadata", {}),
                sla=sla,
            )
        )

    edges: list[GraphEdge] = []
    for ed in data.get("edges", []):
        edges.append(
            GraphEdge(
                id=ed["id"],
                source_id=ed["source_id"],
                target_id=ed["target_id"],
                label=ed.get("label", ""),
                condition=ed.get("condition", ""),
            )
        )

    saas_configs: dict[str, SaaSConfig] = {}
    for key, cfg in data.get("saas_configs", {}).items():
        saas_configs[key] = SaaSConfig(
            provider=SaaSProvider(cfg["provider"]),
            api_key=cfg.get("api_key", ""),
            webhook_url=cfg.get("webhook_url", ""),
            base_url=cfg.get("base_url", ""),
            extra_params=cfg.get("extra_params", {}),
        )

    return TwinModel(
        id=data["id"],
        company_name=data.get("company_name", ""),
        version=data.get("version", "1.0.0"),
        nodes=nodes,
        edges=edges,
        saas_configs=saas_configs,
        pdf_source_path=data.get("pdf_source_path", ""),
        created_at=data.get("created_at", ""),
        description=data.get("description", ""),
    )


def save_twin_config(model: TwinModel, path: Path) -> None:
    path.write_text(json.dumps(twin_to_dict(model), indent=2, ensure_ascii=False), encoding="utf-8")


def load_twin_config(path: Path) -> TwinModel:
    data = json.loads(path.read_text(encoding="utf-8"))
    return twin_from_dict(data)
