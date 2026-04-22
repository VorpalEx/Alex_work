"""
What-if Simulation Engine.

Allows disconnecting the digital twin from live SaaS data and running
scenario analyses: disable nodes, modify durations, compute time savings.
"""
from __future__ import annotations

import copy
from typing import Optional

from digital_twin_factory.shared_logic.models import (
    GraphNode,
    SimulationScenario,
    TwinModel,
)


class SimulationEngine:
    """Compute theoretical process durations under different scenarios."""

    def __init__(self, model: TwinModel) -> None:
        self._base_model = model
        self.current_scenario: Optional[SimulationScenario] = None

    # ------------------------------------------------------------------
    def baseline_total_duration(self) -> float:
        """Sum of all SLA max durations in the base model."""
        return sum(n.sla.max_duration_seconds for n in self._base_model.nodes if n.sla)

    # ------------------------------------------------------------------
    def create_scenario(self, name: str, description: str = "") -> SimulationScenario:
        scenario = SimulationScenario(name=name, description=description)
        scenario.baseline_total_time = self.baseline_total_duration()
        self.current_scenario = scenario
        return scenario

    # ------------------------------------------------------------------
    def disable_node(self, node_id: str) -> None:
        if self.current_scenario and node_id not in self.current_scenario.disabled_nodes:
            self.current_scenario.disabled_nodes.append(node_id)

    def enable_node(self, node_id: str) -> None:
        if self.current_scenario:
            self.current_scenario.disabled_nodes = [
                n for n in self.current_scenario.disabled_nodes if n != node_id
            ]

    def set_node_duration(self, node_id: str, seconds: float) -> None:
        if self.current_scenario:
            self.current_scenario.modified_durations[node_id] = seconds

    # ------------------------------------------------------------------
    def compute(self) -> SimulationResult:
        """
        Evaluate the current scenario and return a SimulationResult
        with timing and impact analysis.
        """
        if not self.current_scenario:
            raise RuntimeError("Aucun scénario actif. Appelez create_scenario() d'abord.")

        disabled = set(self.current_scenario.disabled_nodes)
        modified = self.current_scenario.modified_durations

        node_map: dict[str, GraphNode] = {n.id: n for n in self._base_model.nodes}

        details: list[NodeTimingDetail] = []
        total = 0.0

        for node in self._base_model.nodes:
            if node.id in disabled:
                details.append(NodeTimingDetail(
                    node_id=node.id,
                    label=node.label,
                    base_duration=node.sla.max_duration_seconds if node.sla else 0.0,
                    scenario_duration=0.0,
                    is_disabled=True,
                ))
                continue

            base_dur = node.sla.max_duration_seconds if node.sla else 0.0
            scen_dur = modified.get(node.id, base_dur)
            total += scen_dur
            details.append(NodeTimingDetail(
                node_id=node.id,
                label=node.label,
                base_duration=base_dur,
                scenario_duration=scen_dur,
                is_disabled=False,
            ))

        baseline = self.current_scenario.baseline_total_time
        self.current_scenario.estimated_total_time = total
        savings = baseline - total
        savings_pct = (savings / baseline * 100) if baseline > 0 else 0.0

        return SimulationResult(
            scenario=self.current_scenario,
            total_duration=total,
            baseline_duration=baseline,
            time_savings=savings,
            savings_pct=savings_pct,
            node_details=details,
        )

    # ------------------------------------------------------------------
    def list_node_options(self) -> list[tuple[str, str, float]]:
        """Return list of (node_id, label, base_sla_seconds) for UI display."""
        result = []
        for n in self._base_model.nodes:
            dur = n.sla.max_duration_seconds if n.sla else 0.0
            result.append((n.id, n.label, dur))
        return result


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

class NodeTimingDetail:
    def __init__(
        self,
        node_id: str,
        label: str,
        base_duration: float,
        scenario_duration: float,
        is_disabled: bool,
    ) -> None:
        self.node_id = node_id
        self.label = label
        self.base_duration = base_duration
        self.scenario_duration = scenario_duration
        self.is_disabled = is_disabled

    @property
    def delta(self) -> float:
        return self.scenario_duration - self.base_duration


class SimulationResult:
    def __init__(
        self,
        scenario: SimulationScenario,
        total_duration: float,
        baseline_duration: float,
        time_savings: float,
        savings_pct: float,
        node_details: list[NodeTimingDetail],
    ) -> None:
        self.scenario = scenario
        self.total_duration = total_duration
        self.baseline_duration = baseline_duration
        self.time_savings = time_savings
        self.savings_pct = savings_pct
        self.node_details = node_details

    def format_duration(self, seconds: float) -> str:
        if seconds >= 3600:
            return f"{seconds / 3600:.1f}h"
        if seconds >= 60:
            return f"{seconds / 60:.1f}min"
        return f"{seconds:.0f}s"
