"""
What-if Simulation Panel for the Sentinel.
Allows ADMIN / ANALYST users to disconnect from live data and test scenarios.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.monitoring_engine import MonitoringEngine
from ..core.simulation_engine import SimulationEngine, SimulationResult
from digital_twin_factory.shared_logic.models import TwinModel


class SimulationPanel(QWidget):
    """
    Interactive what-if analysis:
    1. Name the scenario.
    2. Toggle nodes on/off, override durations.
    3. Click 'Simuler' → see time savings.
    """

    def __init__(
        self,
        model: TwinModel,
        engine: MonitoringEngine,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._monitoring_engine = engine
        self._sim = SimulationEngine(model)
        self._node_rows: list[tuple[str, QCheckBox, QDoubleSpinBox]] = []
        self._build_ui()
        self._populate_nodes()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Scenario header
        grp_header = QGroupBox("Nouveau scénario")
        form = QFormLayout(grp_header)
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Ex: Suppression validation manuelle")
        self.input_desc = QLineEdit()
        self.input_desc.setPlaceholderText("Description optionnelle")
        form.addRow("Nom :", self.input_name)
        form.addRow("Description :", self.input_desc)
        root.addWidget(grp_header)

        # Simulation mode toggle
        h_mode = QHBoxLayout()
        self.chk_sim_mode = QCheckBox("Mode Simulation (déconnecte le jumeau du flux réel)")
        self.chk_sim_mode.stateChanged.connect(self._toggle_sim_mode)
        h_mode.addWidget(self.chk_sim_mode)
        root.addLayout(h_mode)

        # Node configuration table
        grp_nodes = QGroupBox("Configuration des nœuds pour le scénario")
        v_nodes = QVBoxLayout(grp_nodes)

        self.nodes_table = QTableWidget(0, 4)
        self.nodes_table.setHorizontalHeaderLabels(["Actif", "Nœud", "SLA de référence (s)", "Durée simulée (s)"])
        self.nodes_table.horizontalHeader().setStretchLastSection(True)
        self.nodes_table.setAlternatingRowColors(True)
        v_nodes.addWidget(self.nodes_table)
        root.addWidget(grp_nodes, 1)

        # Run button
        h_run = QHBoxLayout()
        self.btn_simulate = QPushButton("Lancer la simulation")
        self.btn_simulate.setStyleSheet("background-color: #1f6feb; color: #fff; font-weight: bold; padding: 8px 20px;")
        self.btn_simulate.clicked.connect(self._run_simulation)
        h_run.addStretch()
        h_run.addWidget(self.btn_simulate)
        root.addLayout(h_run)

        # Results group
        grp_results = QGroupBox("Résultats de la simulation")
        v_res = QVBoxLayout(grp_results)
        self.lbl_baseline = QLabel("Durée de référence : —")
        self.lbl_simulated = QLabel("Durée simulée : —")
        self.lbl_savings = QLabel("Gain de temps : —")
        self.lbl_savings.setStyleSheet("color: #3fb950; font-size: 16px; font-weight: bold;")

        self.result_table = QTableWidget(0, 4)
        self.result_table.setHorizontalHeaderLabels(["Nœud", "Référence", "Simulé", "Delta"])
        self.result_table.horizontalHeader().setStretchLastSection(True)

        for lbl in (self.lbl_baseline, self.lbl_simulated, self.lbl_savings):
            v_res.addWidget(lbl)
        v_res.addWidget(self.result_table)
        root.addWidget(grp_results)

    # ------------------------------------------------------------------
    def _populate_nodes(self) -> None:
        self.nodes_table.setRowCount(0)
        self._node_rows.clear()

        for node in self._model.nodes:
            row = self.nodes_table.rowCount()
            self.nodes_table.insertRow(row)

            chk = QCheckBox()
            chk.setChecked(True)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.nodes_table.setCellWidget(row, 0, chk_widget)

            self.nodes_table.setItem(row, 1, QTableWidgetItem(node.label))

            base_dur = node.sla.max_duration_seconds if node.sla else 0.0
            self.nodes_table.setItem(row, 2, QTableWidgetItem(f"{base_dur:.0f}"))

            spin = QDoubleSpinBox()
            spin.setRange(0.0, 86400.0)
            spin.setValue(base_dur)
            spin.setSuffix(" s")
            self.nodes_table.setCellWidget(row, 3, spin)

            self._node_rows.append((node.id, chk, spin))

    # ------------------------------------------------------------------
    def _toggle_sim_mode(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self._monitoring_engine.set_simulation_mode(enabled)

    # ------------------------------------------------------------------
    def _run_simulation(self) -> None:
        name = self.input_name.text().strip() or "Scénario sans nom"
        desc = self.input_desc.text().strip()
        scenario = self._sim.create_scenario(name, desc)

        for node_id, chk_widget, spin in self._node_rows:
            # Retrieve actual QCheckBox from the container widget
            chk: Optional[QCheckBox] = chk_widget.findChild(QCheckBox) if isinstance(chk_widget, QWidget) else chk_widget  # type: ignore
            is_active = chk.isChecked() if chk else True
            if not is_active:
                self._sim.disable_node(node_id)
            else:
                self._sim.set_node_duration(node_id, spin.value())

        result = self._sim.compute()
        self._display_results(result)

    # ------------------------------------------------------------------
    def _display_results(self, result: SimulationResult) -> None:
        fmt = result.format_duration
        self.lbl_baseline.setText(f"Durée de référence : {fmt(result.baseline_duration)}")
        self.lbl_simulated.setText(f"Durée simulée : {fmt(result.total_duration)}")
        savings_txt = f"Gain de temps : {fmt(result.time_savings)}  ({result.savings_pct:.1f}%)"
        self.lbl_savings.setText(savings_txt)

        self.result_table.setRowCount(0)
        for detail in result.node_details:
            row = self.result_table.rowCount()
            self.result_table.insertRow(row)
            self.result_table.setItem(row, 0, QTableWidgetItem(detail.label))
            base_txt = fmt(detail.base_duration) if detail.base_duration else "—"
            scen_txt = "DÉSACTIVÉ" if detail.is_disabled else fmt(detail.scenario_duration)
            delta_txt = "—" if detail.is_disabled else (
                f"{fmt(abs(detail.delta))} {'(gain)' if detail.delta < 0 else '(perte)'}"
            )
            self.result_table.setItem(row, 1, QTableWidgetItem(base_txt))
            self.result_table.setItem(row, 2, QTableWidgetItem(scen_txt))
            delta_item = QTableWidgetItem(delta_txt)
            if not detail.is_disabled and detail.delta < 0:
                delta_item.setForeground(__import__("PyQt6.QtGui", fromlist=["QColor"]).QColor("#3fb950"))
            self.result_table.setItem(row, 3, delta_item)
