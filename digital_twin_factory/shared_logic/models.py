"""Core data models shared between Parent (Builder) and Child (Sentinel)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
import uuid


class NodeType(str, Enum):
    HUMAN = "human"
    AUTOMATED = "automated"
    DECISION = "decision"
    START = "start"
    END = "end"


class StepStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    IDLE = "idle"
    RUNNING = "running"


class SaaSProvider(str, Enum):
    ZAPIER = "zapier"
    MAKE = "make"
    N8N = "n8n"
    CUSTOM = "custom"


class UserRole(str, Enum):
    ADMIN = "admin"       # Can modify thresholds and config
    OPERATOR = "operator" # Real-time view only
    ANALYST = "analyst"   # Access to simulator


@dataclass
class SLARule:
    """Service Level Agreement rule extracted from PDF."""
    step_id: str
    max_duration_seconds: float
    description: str
    warning_threshold_pct: float = 0.20  # 20% overage triggers warning


@dataclass
class GraphNode:
    """Represents a process step in the digital twin graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    node_type: NodeType = NodeType.HUMAN
    description: str = ""
    sla: SLARule | None = None
    saas_provider: SaaSProvider | None = None
    saas_module_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    status: StepStatus = StepStatus.IDLE
    last_duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Directed connection between two process steps."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    condition: str = ""


@dataclass
class SaaSConfig:
    """API credentials for a single SaaS integration."""
    provider: SaaSProvider
    api_key: str = ""
    webhook_url: str = ""
    base_url: str = ""
    extra_params: dict[str, str] = field(default_factory=dict)


@dataclass
class TwinModel:
    """Complete digital twin model: graph + SaaS configs + metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str = ""
    version: str = "1.0.0"
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    saas_configs: dict[str, SaaSConfig] = field(default_factory=dict)
    pdf_source_path: str = ""
    created_at: str = ""
    description: str = ""


@dataclass
class AnomalyEvent:
    """An anomaly detected during real-time monitoring."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    node_label: str = ""
    timestamp: str = ""
    expected_duration: float = 0.0
    actual_duration: float = 0.0
    overage_pct: float = 0.0
    error_message: str = ""
    severity: StepStatus = StepStatus.WARNING


@dataclass
class SimulationScenario:
    """A what-if simulation scenario."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    disabled_nodes: list[str] = field(default_factory=list)
    modified_durations: dict[str, float] = field(default_factory=dict)
    estimated_total_time: float = 0.0
    baseline_total_time: float = 0.0
