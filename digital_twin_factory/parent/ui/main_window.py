"""Main window for the Parent (Builder) application."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
)
from PyQt6.QtGui import QAction

from .pdf_ingestion_panel import PDFIngestionPanel
from .saas_config_panel import SaaSConfigPanel
from .graph_view_panel import GraphViewPanel
from .build_panel import BuildPanel
from .styles import DARK_STYLESHEET
from ..core.graph_builder import GraphBuilder
from ...shared_logic.graph_schema import save_twin_config, load_twin_config
from ...shared_logic.models import TwinModel


class ParentMainWindow(QMainWindow):
    """
    Four-tab industrial dashboard:
    1. Ingestion PDF
    2. Configuration SaaS
    3. Graphe du Jumeau
    4. Génération .exe
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Digital Twin Factory — Builder v1.0")
        self.resize(1280, 800)
        self.setStyleSheet(DARK_STYLESHEET)

        self._builder = GraphBuilder()
        self._model: TwinModel = self._builder.model

        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

    # ------------------------------------------------------------------
    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Fichier")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new = QAction("Nouveau projet", self)
        act_new.triggered.connect(self._new_project)
        toolbar.addAction(act_new)

        act_open = QAction("Ouvrir config.json", self)
        act_open.triggered.connect(self._open_config)
        toolbar.addAction(act_open)

        act_save = QAction("Sauvegarder config.json", self)
        act_save.triggered.connect(self._save_config)
        toolbar.addAction(act_save)

        toolbar.addSeparator()

        act_about = QAction("À propos", self)
        act_about.triggered.connect(self._about)
        toolbar.addAction(act_about)

    # ------------------------------------------------------------------
    def _build_tabs(self) -> None:
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 1: PDF ingestion
        self.tab_pdf = PDFIngestionPanel()
        self.tab_pdf.model_extracted.connect(self._on_model_extracted)
        tabs.addTab(self.tab_pdf, "1 · Ingestion PDF")

        # Tab 2: SaaS configuration
        self.tab_saas = SaaSConfigPanel()
        self.tab_saas.saas_updated.connect(self._on_saas_updated)
        tabs.addTab(self.tab_saas, "2 · Configuration SaaS")

        # Tab 3: Graph view
        self.tab_graph = GraphViewPanel()
        tabs.addTab(self.tab_graph, "3 · Graphe du Jumeau")

        # Tab 4: Build
        self.tab_build = BuildPanel()
        tabs.addTab(self.tab_build, "4 · Générer .exe Enfant")

        self.setCentralWidget(tabs)

    # ------------------------------------------------------------------
    def _build_statusbar(self) -> None:
        bar = QStatusBar()
        self.lbl_status = QLabel("Prêt  —  Aucun projet chargé")
        self.lbl_status.setStyleSheet("color: #8b949e; padding: 2px 6px;")
        bar.addWidget(self.lbl_status)
        self.setStatusBar(bar)

    # ------------------------------------------------------------------
    def _set_status(self, msg: str) -> None:
        self.lbl_status.setText(msg)

    # ------------------------------------------------------------------
    def _on_model_extracted(self, model: TwinModel) -> None:
        self._model = model
        self._builder = GraphBuilder(model)
        self.tab_saas.set_model(model)
        self.tab_graph.set_model(model)
        self.tab_build.set_model(model)
        n = len(model.nodes)
        self._set_status(
            f"Modèle chargé — {model.company_name}  |  {n} nœuds  |  {len(model.edges)} arêtes"
        )

    # ------------------------------------------------------------------
    def _on_saas_updated(self, _configs: dict) -> None:
        self.tab_graph.refresh()
        self._set_status("Configuration SaaS mise à jour.")

    # ------------------------------------------------------------------
    def _new_project(self) -> None:
        confirm = QMessageBox.question(self, "Nouveau projet", "Effacer le projet courant ?")
        if confirm == QMessageBox.StandardButton.Yes:
            self._model = TwinModel()
            self._builder = GraphBuilder(self._model)
            self.tab_graph.set_model(self._model)
            self.tab_build.set_model(self._model)
            self._set_status("Nouveau projet créé.")

    def _open_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir config.json", "", "JSON (*.json)")
        if path:
            try:
                model = load_twin_config(Path(path))
                self._on_model_extracted(model)
                self._set_status(f"Configuration chargée : {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", str(exc))

    def _save_config(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder config.json", "config.json", "JSON (*.json)")
        if path:
            try:
                save_twin_config(self._model, Path(path))
                self._set_status(f"Configuration sauvegardée : {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Erreur", str(exc))

    def _about(self) -> None:
        QMessageBox.information(
            self,
            "Digital Twin Factory — Builder",
            "Version 1.0\n\nOutil de modélisation de jumeaux numériques.\n\n"
            "Stack : Python 3.11 · PyQt6 · LangChain · NetworkX · PyInstaller",
        )
