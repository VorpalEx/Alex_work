"""Panel: PDF ingestion + RAG extraction into the dependency graph."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.pdf_processor import PDFProcessor
from ...shared_logic.models import TwinModel


class _ExtractionWorker(QThread):
    finished = pyqtSignal(object)   # TwinModel
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self, pdf_path: str, company_name: str, openai_key: str) -> None:
        super().__init__()
        self.pdf_path = pdf_path
        self.company_name = company_name
        self.openai_key = openai_key

    def run(self) -> None:
        try:
            self.log.emit(f"Chargement du PDF : {self.pdf_path}")
            processor = PDFProcessor(self.pdf_path, self.company_name, self.openai_key)
            self.log.emit("Extraction des étapes en cours (RAG) …")
            model = processor.extract_twin_model()
            self.log.emit(f"Extraction terminée — {len(model.nodes)} nœuds, {len(model.edges)} arêtes détectés.")
            self.finished.emit(model)
        except Exception as exc:
            self.error.emit(str(exc))


class PDFIngestionPanel(QWidget):
    """
    Lets the user pick a PDF, enter company name + optional OpenAI key,
    then triggers extraction.  Emits model_extracted(TwinModel) when done.
    """

    model_extracted = pyqtSignal(object)  # TwinModel

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._pdf_path: str = ""
        self._worker: Optional[_ExtractionWorker] = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        # --- PDF selection ---
        grp_pdf = QGroupBox("Document source (PDF)")
        v_pdf = QVBoxLayout(grp_pdf)

        h_file = QHBoxLayout()
        self.lbl_file = QLabel("Aucun fichier sélectionné")
        self.lbl_file.setStyleSheet("color: #8b949e;")
        btn_browse = QPushButton("Parcourir…")
        btn_browse.clicked.connect(self._browse_pdf)
        h_file.addWidget(self.lbl_file, 1)
        h_file.addWidget(btn_browse)
        v_pdf.addLayout(h_file)
        root.addWidget(grp_pdf)

        # --- Company info ---
        grp_info = QGroupBox("Informations client")
        v_info = QVBoxLayout(grp_info)

        h_company = QHBoxLayout()
        h_company.addWidget(QLabel("Nom de l'entreprise :"))
        self.input_company = QLineEdit()
        self.input_company.setPlaceholderText("Acme Corp")
        h_company.addWidget(self.input_company)
        v_info.addLayout(h_company)

        h_key = QHBoxLayout()
        h_key.addWidget(QLabel("Clé OpenAI (optionnel) :"))
        self.input_openai = QLineEdit()
        self.input_openai.setPlaceholderText("sk-…  (laissez vide pour l'extraction heuristique)")
        self.input_openai.setEchoMode(QLineEdit.EchoMode.Password)
        h_key.addWidget(self.input_openai)
        v_info.addLayout(h_key)
        root.addWidget(grp_info)

        # --- Actions ---
        h_actions = QHBoxLayout()
        self.btn_extract = QPushButton("Extraire le Jumeau Numérique")
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self._start_extraction)
        h_actions.addStretch()
        h_actions.addWidget(self.btn_extract)
        root.addLayout(h_actions)

        # --- Progress ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        # --- Log output ---
        grp_log = QGroupBox("Journal d'extraction")
        v_log = QVBoxLayout(grp_log)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(150)
        v_log.addWidget(self.log_view)
        root.addWidget(grp_log, 1)

    # ------------------------------------------------------------------
    def _browse_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un PDF", "", "PDF Files (*.pdf)")
        if path:
            self._pdf_path = path
            self.lbl_file.setText(Path(path).name)
            self.btn_extract.setEnabled(True)

    # ------------------------------------------------------------------
    def _start_extraction(self) -> None:
        if not self._pdf_path:
            return
        self.progress.setVisible(True)
        self.btn_extract.setEnabled(False)
        self.log_view.clear()

        self._worker = _ExtractionWorker(
            self._pdf_path,
            self.input_company.text().strip(),
            self.input_openai.text().strip(),
        )
        self._worker.log.connect(self._append_log)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _append_log(self, msg: str) -> None:
        self.log_view.append(msg)

    def _on_done(self, model: TwinModel) -> None:
        self.progress.setVisible(False)
        self.btn_extract.setEnabled(True)
        self._append_log("✓ Modèle construit avec succès.")
        self.model_extracted.emit(model)

    def _on_error(self, msg: str) -> None:
        self.progress.setVisible(False)
        self.btn_extract.setEnabled(True)
        self._append_log(f"✗ Erreur : {msg}")
        QMessageBox.critical(self, "Erreur d'extraction", msg)
