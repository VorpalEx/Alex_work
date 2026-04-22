"""
Anomaly detector: maintains an in-memory log of anomalies,
applies deduplication, and provides query helpers for the UI.
"""
from __future__ import annotations

import datetime
from collections import deque
from typing import Deque, Optional

from digital_twin_factory.shared_logic.models import AnomalyEvent, StepStatus


_MAX_HISTORY = 500


class AnomalyDetector:
    """Thread-safe in-memory anomaly store with deduplication."""

    def __init__(self) -> None:
        self._log: Deque[AnomalyEvent] = deque(maxlen=_MAX_HISTORY)
        self._active: dict[str, AnomalyEvent] = {}   # node_id → current anomaly

    # ------------------------------------------------------------------
    def record(self, event: AnomalyEvent) -> bool:
        """
        Add event to the log.  Returns True if this is a new anomaly
        (not a duplicate of the last event for this node within 60s).
        """
        prev = self._active.get(event.node_id)
        if prev and abs(float(prev.timestamp) - float(event.timestamp)) < 60:
            return False
        self._log.appendleft(event)
        self._active[event.node_id] = event
        return True

    def clear_node(self, node_id: str) -> None:
        self._active.pop(node_id, None)

    def clear_all(self) -> None:
        self._log.clear()
        self._active.clear()

    # ------------------------------------------------------------------
    def get_history(
        self,
        severity: Optional[StepStatus] = None,
        node_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AnomalyEvent]:
        result = list(self._log)
        if severity:
            result = [e for e in result if e.severity == severity]
        if node_id:
            result = [e for e in result if e.node_id == node_id]
        return result[:limit]

    def get_active_anomalies(self) -> dict[str, AnomalyEvent]:
        return dict(self._active)

    def error_count(self) -> int:
        return sum(1 for e in self._active.values() if e.severity == StepStatus.ERROR)

    def warning_count(self) -> int:
        return sum(1 for e in self._active.values() if e.severity == StepStatus.WARNING)

    def format_timestamp(self, ts: str) -> str:
        try:
            return datetime.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ts
