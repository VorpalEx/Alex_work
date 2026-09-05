"""Panel: generate the Child .exe from the current TwinModel."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.build_engine import BuildEngine
from ...shared_logic.models import TwinModel


class _BuildWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal(str)   # path to produced exe
    error = pyqtSignal(str)

    def __init__(self, model: TwinModel, output_dir: str) -> None:
        super().__init__()
        self.model = model
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            engine = BuildEngine(
                self.model,
                output_dir=Path(self.output_dir),
                progress_callback=self.log.emit,
            )
            path = engine.build()
            self.finished.emit(str(path))
        except Exception as exc:
            self.error.emit(str(exc))


class BuildPanel(QWidget):
    """
    UI for the 'Generate Child .exe' step.
    Validates the model, asks for an output directory, then runs BuildEngine
    in a background QThread to keep the UI responsive.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[TwinModel] = None
        self._output_dir: str = str(Path.home() / "DigitalTwin_Output")
        self._worker: Optional[_BuildWorker] = None
        self._build_ui()

    # ------------------------------------------------------------------
    def set_model(self, model: TwinModel) -> None:
        self._model = model
        self._refresh_summary()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)

        # Summary
        grp_summary = QGroupBox("Résumé du Jumeau Numérique")
        v_sum = QVBoxLayout(grp_summary)
        self.lbl_company = QLabel("Entreprise : —")
        self.lbl_nodes = QLabel("Nœuds : —")
        self.lbl_saas = QLabel("Intégrations SaaS : —")
        self.lbl_sla = QLabel("Règles SLA : —")
        for lbl in (self.lbl_company, self.lbl_nodes, self.lbl_saas, self.lbl_sla):
            v_sum.addWidget(lbl)
        root.addWidget(grp_summary)

        # Output directory
        grp_out = QGroupBox("Dossier de sortie")
        h_out = QHBoxLayout(grp_out)
        self.lbl_out_dir = QLabel(self._output_dir)
        self.lbl_out_dir.setStyleSheet("color: #58a6ff;")
        btn_choose = QPushButton("Choisir…")
        btn_choose.clicked.connect(self._choose_output)
        h_out.addWidget(self.lbl_out_dir, 1)
        h_out.addWidget(btn_choose)
        root.addWidget(grp_out)

        # Build button
        h_build = QHBoxLayout()
        self.btn_build = QPushButton("Générer le .exe Enfant")
        self.btn_build.setObjectName("build_btn")
        self.btn_build.setEnabled(False)
        self.btn_build.clicked.connect(self._start_build)
        h_build.addStretch()
        h_build.addWidget(self.btn_build)
        root.addLayout(h_build)

        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # Build log
        grp_log = QGroupBox("Journal de compilation")
        v_log = QVBoxLayout(grp_log)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        v_log.addWidget(self.log_view)
        root.addWidget(grp_log, 1)

    # ------------------------------------------------------------------
    def _refresh_summary(self) -> None:
        if not self._model:
            return
        self.lbl_company.setText(f"Entreprise : {self._model.company_name or '(non défini)'}")
        self.lbl_nodes.setText(f"Nœuds : {len(self._model.nodes)}")
        saas_count = sum(1 for n in self._model.nodes if n.saas_provider)
        self.lbl_saas.setText(f"Intégrations SaaS : {saas_count}")
        sla_count = sum(1 for n in self._model.nodes if n.sla)
        self.lbl_sla.setText(f"Règles SLA : {sla_count}")
        self.btn_build.setEnabled(len(self._model.nodes) > 0)

    # ------------------------------------------------------------------
    def _choose_output(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Dossier de sortie", self._output_dir)
        if d:
            self._output_dir = d
            self.lbl_out_dir.setText(d)

    # ------------------------------------------------------------------
    def _start_build(self) -> None:
        if not self._model:
            return
        confirm = QMessageBox.question(
            self,
            "Générer l'exécutable",
            f"Générer DigitalTwin_{self._model.company_name}.exe dans :\n{self._output_dir} ?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.progress.setVisible(True)
        self.btn_build.setEnabled(False)
        self.log_view.clear()

        self._worker = _BuildWorker(self._model, self._output_dir)
        self._worker.log.connect(self._append_log)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _append_log(self, msg: str) -> None:
        self.log_view.append(msg)

    def _on_done(self, path: str) -> None:
        self.progress.setVisible(False)
        self.btn_build.setEnabled(True)
        self._append_log(f"\n✓ Build réussi → {path}")
        QMessageBox.information(self, "Build terminé", f"Exécutable généré :\n{path}")

    def _on_error(self, msg: str) -> None:
        self.progress.setVisible(False)
        self.btn_build.setEnabled(True)
        self._append_log(f"\n✗ ERREUR : {msg}")
        QMessageBox.critical(self, "Erreur de Build", msg)
