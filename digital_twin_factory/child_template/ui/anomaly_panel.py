"""Anomaly history table panel for the Sentinel."""
from __future__ import annotations

import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.anomaly_detector import AnomalyDetector
from digital_twin_factory.shared_logic.models import AnomalyEvent, StepStatus


_SEVERITY_COLORS = {
    StepStatus.ERROR:   "#f85149",
    StepStatus.WARNING: "#d29922",
    StepStatus.OK:      "#3fb950",
}


class AnomalyPanel(QWidget):
    """
    Displays the full anomaly history in a sortable table.
    Receives anomaly events from the MonitoringEngine via a shared detector.
    """

    def __init__(self, detector: AnomalyDetector, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._detector = detector
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Header + controls
        h_top = QHBoxLayout()
        lbl_title = QLabel("Journal des Anomalies")
        lbl_title.setObjectName("section_title")
        btn_clear = QPushButton("Effacer l'historique")
        btn_clear.clicked.connect(self._clear)
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.clicked.connect(self._refresh)
        h_top.addWidget(lbl_title)
        h_top.addStretch()
        h_top.addWidget(btn_refresh)
        h_top.addWidget(btn_clear)
        root.addLayout(h_top)

        # Summary KPIs
        h_kpi = QHBoxLayout()
        self.lbl_total = QLabel("Total : 0")
        self.lbl_errors = QLabel("Erreurs : 0")
        self.lbl_errors.setStyleSheet("color: #f85149; font-weight: bold;")
        self.lbl_warnings = QLabel("Alertes : 0")
        self.lbl_warnings.setStyleSheet("color: #d29922; font-weight: bold;")
        for lbl in (self.lbl_total, self.lbl_errors, self.lbl_warnings):
            h_kpi.addWidget(lbl)
        h_kpi.addStretch()
        root.addLayout(h_kpi)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Horodatage", "Nœud", "Sévérité", "Durée attendue", "Durée réelle", "Dépassement"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        root.addWidget(self.table, 1)

    # ------------------------------------------------------------------
    @pyqtSlot(object)
    def add_anomaly(self, event: AnomalyEvent) -> None:
        is_new = self._detector.record(event)
        if is_new:
            self._insert_row(event)
            self._update_kpis()

    # ------------------------------------------------------------------
    def _insert_row(self, event: AnomalyEvent) -> None:
        row = 0  # Insert at top
        self.table.insertRow(row)

        ts = self._detector.format_timestamp(event.timestamp)
        sev_color = _SEVERITY_COLORS.get(event.severity, "#c9d1d9")

        cells = [
            ts,
            event.node_label,
            event.severity.value.upper(),
            f"{event.expected_duration:.0f}s" if event.expected_duration else "—",
            f"{event.actual_duration:.0f}s" if event.actual_duration else "—",
            f"+{event.overage_pct * 100:.1f}%" if event.overage_pct else event.error_message,
        ]
        for col, text in enumerate(cells):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if col == 2:
                item.setForeground(Qt.GlobalColor.white)
                item.setBackground(
                    __import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(sev_color)
                )
            self.table.setItem(row, col, item)

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        self.table.setRowCount(0)
        for event in self._detector.get_history():
            self._insert_row(event)
        self._update_kpis()

    def _clear(self) -> None:
        self._detector.clear_all()
        self.table.setRowCount(0)
        self._update_kpis()

    def _update_kpis(self) -> None:
        history = self._detector.get_history()
        self.lbl_total.setText(f"Total : {len(history)}")
        self.lbl_errors.setText(f"Erreurs : {self._detector.error_count()}")
        self.lbl_warnings.setText(f"Alertes : {self._detector.warning_count()}")
