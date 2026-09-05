"""
T-1min Monitoring Engine.

Polls every 60 seconds and compares real SaaS execution data
against the theoretical SLA rules embedded in the TwinModel.
Emits anomaly events when a deviation > threshold is detected.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QThread, pyqtSignal

# Allow running child_template as a standalone package
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from digital_twin_factory.shared_logic.models import (
    AnomalyEvent,
    GraphNode,
    SaaSProvider,
    StepStatus,
    TwinModel,
)

try:
    from digital_twin_factory.parent.core.saas_connector import make_connector, ExecutionRecord
    _CONNECTOR_AVAILABLE = True
except ImportError:
    _CONNECTOR_AVAILABLE = False


class MonitoringEngine(QThread):
    """
    Background thread: polls SaaS providers every POLL_INTERVAL seconds,
    computes deviations, and emits signals for the UI.
    """

    POLL_INTERVAL = 60  # seconds (T-1min)

    node_status_changed = pyqtSignal(str, str)   # (node_id, StepStatus value)
    anomaly_detected = pyqtSignal(object)         # AnomalyEvent
    cycle_complete = pyqtSignal(float)            # timestamp of last poll

    def __init__(self, model: TwinModel) -> None:
        super().__init__()
        self.model = model
        self._running = False
        self._simulation_mode = False
        self._node_map: dict[str, GraphNode] = {n.id: n for n in model.nodes}

    # ------------------------------------------------------------------
    def start_monitoring(self) -> None:
        self._running = True
        self.start()

    def stop_monitoring(self) -> None:
        self._running = False
        self.wait(3000)

    def set_simulation_mode(self, enabled: bool) -> None:
        self._simulation_mode = enabled

    # ------------------------------------------------------------------
    def run(self) -> None:
        while self._running:
            if not self._simulation_mode:
                self._poll_cycle()
            time.sleep(self.POLL_INTERVAL)

    # ------------------------------------------------------------------
    def _poll_cycle(self) -> None:
        """One monitoring cycle: fetch executions, compare to SLAs."""
        now = time.time()

        # Collect latest execution per module from each configured provider
        latest: dict[str, "ExecutionRecord"] = {}

        if _CONNECTOR_AVAILABLE:
            for provider_key, cfg in self.model.saas_configs.items():
                connector = make_connector(cfg)
                records = connector.get_recent_executions(limit=100)
                for rec in records:
                    # Last record per module_id
                    if rec.module_id not in latest or rec.started_at > latest[rec.module_id].started_at:
                        latest[rec.module_id] = rec

        # Match nodes to execution records
        for node in self.model.nodes:
            if not node.saas_module_id:
                continue
            rec = latest.get(node.saas_module_id)
            if rec is None:
                self.node_status_changed.emit(node.id, StepStatus.IDLE.value)
                continue

            # Update node status from the SaaS record
            node.status = rec.status
            self.node_status_changed.emit(node.id, rec.status.value)

            # SLA check
            if node.sla:
                threshold_pct = node.sla.warning_threshold_pct
                max_dur = node.sla.max_duration_seconds
                actual = rec.duration_seconds

                if actual > max_dur * (1 + threshold_pct):
                    overage = (actual - max_dur) / max_dur
                    severity = StepStatus.ERROR if overage > 0.5 else StepStatus.WARNING
                    anomaly = AnomalyEvent(
                        node_id=node.id,
                        node_label=node.label,
                        timestamp=str(now),
                        expected_duration=max_dur,
                        actual_duration=actual,
                        overage_pct=overage,
                        error_message=rec.error_message,
                        severity=severity,
                    )
                    node.status = severity
                    self.node_status_changed.emit(node.id, severity.value)
                    self.anomaly_detected.emit(anomaly)

            elif rec.status == StepStatus.ERROR:
                anomaly = AnomalyEvent(
                    node_id=node.id,
                    node_label=node.label,
                    timestamp=str(now),
                    error_message=rec.error_message or "Erreur SaaS détectée",
                    severity=StepStatus.ERROR,
                )
                self.anomaly_detected.emit(anomaly)

        self.cycle_complete.emit(now)
