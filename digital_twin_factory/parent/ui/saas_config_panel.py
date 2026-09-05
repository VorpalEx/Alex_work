"""Panel: SaaS credentials + mapping of modules to graph nodes."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.saas_connector import make_connector
from ...shared_logic.models import SaaSConfig, SaaSProvider, TwinModel


class SaaSConfigPanel(QWidget):
    """
    Three sub-sections (Zapier / Make / n8n) for entering API credentials.
    A mapping table lets the user bind each graph node to a SaaS module.
    Emits saas_updated(dict[str, SaaSConfig]) when the user applies changes.
    """

    saas_updated = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[TwinModel] = None
        self._credential_inputs: dict[str, dict[str, QLineEdit]] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    def set_model(self, model: TwinModel) -> None:
        self._model = model
        self._refresh_mapping_table()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ---- Credentials per provider ----
        for provider, label in [
            (SaaSProvider.ZAPIER, "Zapier"),
            (SaaSProvider.MAKE, "Make.com"),
            (SaaSProvider.N8N, "n8n"),
        ]:
            grp = QGroupBox(label)
            form = QFormLayout(grp)

            api_input = QLineEdit()
            api_input.setPlaceholderText("API Key / Token")
            api_input.setEchoMode(QLineEdit.EchoMode.Password)

            wh_input = QLineEdit()
            wh_input.setPlaceholderText("Webhook URL (optionnel)")

            base_input = QLineEdit()
            base_input.setPlaceholderText("Base URL (optionnel, pour n8n self-hosted)")

            form.addRow("API Key :", api_input)
            form.addRow("Webhook :", wh_input)
            form.addRow("Base URL :", base_input)

            h_btn = QHBoxLayout()
            test_btn = QPushButton(f"Tester {label}")
            test_btn.clicked.connect(lambda _=False, p=provider: self._test_connection(p))
            self.lbl_status = QLabel("—")
            h_btn.addWidget(test_btn)
            h_btn.addWidget(self.lbl_status)
            h_btn.addStretch()
            form.addRow("", h_btn)

            self._credential_inputs[provider.value] = {
                "api_key": api_input,
                "webhook_url": wh_input,
                "base_url": base_input,
            }
            root.addWidget(grp)

        # ---- Mapping table (Node → SaaS Module) ----
        grp_map = QGroupBox("Mapping Nœud du Graphe → Module SaaS")
        v_map = QVBoxLayout(grp_map)

        self.mapping_table = QTableWidget(0, 4)
        self.mapping_table.setHorizontalHeaderLabels(["Nœud", "Type", "Provider", "Module ID"])
        self.mapping_table.horizontalHeader().setStretchLastSection(True)
        self.mapping_table.setAlternatingRowColors(True)
        v_map.addWidget(self.mapping_table)

        btn_apply = QPushButton("Appliquer la configuration SaaS")
        btn_apply.clicked.connect(self._apply)
        v_map.addWidget(btn_apply, alignment=Qt.AlignmentFlag.AlignRight)
        root.addWidget(grp_map, 1)

    # ------------------------------------------------------------------
    def _build_config(self, provider: SaaSProvider) -> SaaSConfig:
        inputs = self._credential_inputs[provider.value]
        return SaaSConfig(
            provider=provider,
            api_key=inputs["api_key"].text().strip(),
            webhook_url=inputs["webhook_url"].text().strip(),
            base_url=inputs["base_url"].text().strip(),
        )

    # ------------------------------------------------------------------
    def _test_connection(self, provider: SaaSProvider) -> None:
        cfg = self._build_config(provider)
        if not cfg.api_key:
            QMessageBox.warning(self, "Clé manquante", "Entrez une API Key avant de tester.")
            return
        connector = make_connector(cfg)
        ok = connector.test_connection()
        msg = "Connexion réussie ✓" if ok else "Connexion échouée ✗"
        QMessageBox.information(self, f"Test {provider.value}", msg)

    # ------------------------------------------------------------------
    def _refresh_mapping_table(self) -> None:
        if not self._model:
            return
        self.mapping_table.setRowCount(0)
        for node in self._model.nodes:
            row = self.mapping_table.rowCount()
            self.mapping_table.insertRow(row)
            self.mapping_table.setItem(row, 0, QTableWidgetItem(node.label))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(node.node_type.value))

            combo = QComboBox()
            for p in SaaSProvider:
                combo.addItem(p.value)
            if node.saas_provider:
                combo.setCurrentText(node.saas_provider.value)
            self.mapping_table.setCellWidget(row, 2, combo)

            mod_input = QLineEdit(node.saas_module_id)
            mod_input.setPlaceholderText("ID Workflow/Zap/Scenario")
            self.mapping_table.setCellWidget(row, 3, mod_input)

    # ------------------------------------------------------------------
    def _apply(self) -> None:
        if not self._model:
            return
        # Collect SaaS configs
        configs: dict[str, SaaSConfig] = {}
        for provider in SaaSProvider:
            inputs = self._credential_inputs.get(provider.value)
            if inputs and inputs["api_key"].text().strip():
                configs[provider.value] = self._build_config(provider)

        # Apply node mappings
        for row, node in enumerate(self._model.nodes):
            combo: QComboBox = self.mapping_table.cellWidget(row, 2)  # type: ignore[assignment]
            mod_input: QLineEdit = self.mapping_table.cellWidget(row, 3)  # type: ignore[assignment]
            if combo and mod_input:
                node.saas_provider = SaaSProvider(combo.currentText())
                node.saas_module_id = mod_input.text().strip()

        self._model.saas_configs = configs
        self.saas_updated.emit(configs)
        QMessageBox.information(self, "Configuration SaaS", "Configuration appliquée avec succès.")
