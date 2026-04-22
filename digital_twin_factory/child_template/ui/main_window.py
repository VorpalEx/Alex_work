"""Main window for the Child (Sentinel) application."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
)

# Allow standalone execution
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from digital_twin_factory.parent.ui.styles import DARK_STYLESHEET
from digital_twin_factory.shared_logic.models import TwinModel, UserRole

from .login_dialog import LoginDialog
from .monitoring_panel import MonitoringPanel
from .anomaly_panel import AnomalyPanel
from .simulation_panel import SimulationPanel
from ..core.anomaly_detector import AnomalyDetector
from ..core.auth_manager import AuthManager


class SentinelMainWindow(QMainWindow):
    """
    Three-tab Sentinel dashboard:
    1. Monitoring temps réel (OPERATOR+)
    2. Anomalies (OPERATOR+)
    3. Simulateur (ANALYST+)
    """

    def __init__(self, model: TwinModel) -> None:
        super().__init__()
        self._model = model
        self._auth = AuthManager()
        self._detector = AnomalyDetector()

        self.setWindowTitle(
            f"Digital Twin Sentinel — {model.company_name}  |  v{model.version}"
        )
        self.resize(1280, 800)
        self.setStyleSheet(DARK_STYLESHEET)

        if not self._do_login():
            sys.exit(0)

        self._build_ui()
        self._apply_rbac()
        self._connect_signals()

    # ------------------------------------------------------------------
    def _do_login(self) -> bool:
        dlg = LoginDialog(self._auth)
        dlg.setStyleSheet(DARK_STYLESHEET)
        return dlg.exec() == LoginDialog.DialogCode.Accepted

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 1: Monitoring
        self.monitoring_panel = MonitoringPanel(self._model)
        self.monitoring_panel.graph_view  # ensure created
        self.tabs.addTab(self.monitoring_panel, "1 · Monitoring Temps Réel")

        # Tab 2: Anomalies
        self.anomaly_panel = AnomalyPanel(self._detector)
        self.tabs.addTab(self.anomaly_panel, "2 · Anomalies")

        # Tab 3: Simulator (visibility controlled by RBAC)
        self.simulation_panel = SimulationPanel(
            self._model, self.monitoring_panel._engine
        )
        self.tabs.addTab(self.simulation_panel, "3 · Simulateur What-if")

        self.setCentralWidget(self.tabs)
        self._build_statusbar()

    # ------------------------------------------------------------------
    def _build_statusbar(self) -> None:
        bar = QStatusBar()
        role = self._auth.current_role.value.upper() if self._auth.current_role else "—"
        self.lbl_user = QLabel(
            f"Utilisateur : {self._auth.current_user}  |  Rôle : {role}"
        )
        self.lbl_user.setStyleSheet("color: #8b949e; padding: 2px 6px;")
        self.lbl_company = QLabel(f"Entreprise : {self._model.company_name}")
        self.lbl_company.setStyleSheet("color: #58a6ff; padding: 2px 6px;")
        bar.addWidget(self.lbl_user)
        bar.addPermanentWidget(self.lbl_company)
        self.setStatusBar(bar)

    # ------------------------------------------------------------------
    def _apply_rbac(self) -> None:
        """Show/hide tabs based on current user role."""
        if not self._auth.can_run_simulation():
            self.tabs.setTabVisible(2, False)
        if not self._auth.can_view_realtime():
            self.tabs.setTabVisible(0, False)
            self.tabs.setTabVisible(1, False)

    # ------------------------------------------------------------------
    def _connect_signals(self) -> None:
        self.monitoring_panel._engine.anomaly_detected.connect(
            self.anomaly_panel.add_anomaly
        )

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.monitoring_panel.stop_engine()
        super().closeEvent(event)
