"""Real-time monitoring panel for the Child (Sentinel)."""
from __future__ import annotations

import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .graph_view import SentinelGraphView
from ..core.monitoring_engine import MonitoringEngine
from digital_twin_factory.shared_logic.models import AnomalyEvent, StepStatus, TwinModel


class MonitoringPanel(QWidget):
    """
    Tab 1 of the Sentinel dashboard.
    Shows the live graph + KPI strip + start/stop controls.
    """

    def __init__(self, model: TwinModel, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model = model
        self._engine = MonitoringEngine(model)
        self._engine.node_status_changed.connect(self._on_status_changed)
        self._engine.anomaly_detected.connect(self._on_anomaly)
        self._engine.cycle_complete.connect(self._on_cycle)
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # KPI strip
        h_kpi = QHBoxLayout()
        self.lbl_last_poll = self._kpi_label("Dernier poll", "—")
        self.lbl_nodes_ok = self._kpi_label("Nœuds OK", "0", "#3fb950")
        self.lbl_warnings = self._kpi_label("Alertes", "0", "#d29922")
        self.lbl_errors = self._kpi_label("Erreurs", "0", "#f85149")
        for kpi in (self.lbl_last_poll, self.lbl_nodes_ok, self.lbl_warnings, self.lbl_errors):
            h_kpi.addWidget(kpi, 1)
        root.addLayout(h_kpi)

        # Graph
        self.graph_view = SentinelGraphView()
        self.graph_view.set_model(self._model)
        root.addWidget(self.graph_view, 1)

        # Controls
        h_ctrl = QHBoxLayout()
        self.btn_start = QPushButton("▶  Démarrer le monitoring")
        self.btn_start.setStyleSheet("background-color: #238636; color: #fff; font-weight: bold;")
        self.btn_start.clicked.connect(self._start)

        self.btn_stop = QPushButton("■  Arrêter")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop)

        self.lbl_status = QLabel("En attente…")
        self.lbl_status.setStyleSheet("color: #8b949e;")

        h_ctrl.addWidget(self.btn_start)
        h_ctrl.addWidget(self.btn_stop)
        h_ctrl.addStretch()
        h_ctrl.addWidget(self.lbl_status)
        root.addLayout(h_ctrl)

    # ------------------------------------------------------------------
    def _kpi_label(self, title: str, value: str, color: str = "#c9d1d9") -> QGroupBox:
        grp = QGroupBox(title)
        v = QVBoxLayout(grp)
        lbl = QLabel(value)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {color};")
        lbl.setObjectName(f"kpi_{title}")
        v.addWidget(lbl)
        grp._value_label = lbl  # type: ignore[attr-defined]
        return grp

    # ------------------------------------------------------------------
    def _start(self) -> None:
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.lbl_status.setText("Monitoring actif (T−1min)")
        self._engine.start_monitoring()

    def _stop(self) -> None:
        self._engine.stop_monitoring()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Monitoring arrêté.")

    # ------------------------------------------------------------------
    @pyqtSlot(str, str)
    def _on_status_changed(self, node_id: str, status_val: str) -> None:
        node = next((n for n in self._model.nodes if n.id == node_id), None)
        if node:
            node.status = StepStatus(status_val)
        self.graph_view.update()
        self._refresh_kpis()

    @pyqtSlot(object)
    def _on_anomaly(self, _event: AnomalyEvent) -> None:
        self._refresh_kpis()

    @pyqtSlot(float)
    def _on_cycle(self, ts: float) -> None:
        dt = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        self.lbl_last_poll._value_label.setText(dt)  # type: ignore[attr-defined]

    def _refresh_kpis(self) -> None:
        ok = sum(1 for n in self._model.nodes if n.status == StepStatus.OK)
        warn = sum(1 for n in self._model.nodes if n.status == StepStatus.WARNING)
        err = sum(1 for n in self._model.nodes if n.status == StepStatus.ERROR)
        self.lbl_nodes_ok._value_label.setText(str(ok))  # type: ignore[attr-defined]
        self.lbl_warnings._value_label.setText(str(warn))  # type: ignore[attr-defined]
        self.lbl_errors._value_label.setText(str(err))  # type: ignore[attr-defined]

    def stop_engine(self) -> None:
        """Called on window close to cleanly stop the background thread."""
        if self._engine.isRunning():
            self._engine.stop_monitoring()
