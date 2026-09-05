"""Login dialog: shown at startup before the main window."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from ..core.auth_manager import AuthManager


class LoginDialog(QDialog):
    def __init__(self, auth: AuthManager) -> None:
        super().__init__()
        self._auth = auth
        self.setWindowTitle("Digital Twin Sentinel — Connexion")
        self.setFixedSize(380, 220)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("Digital Twin Sentinel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff; margin-bottom: 12px;")
        layout.addWidget(title)

        form = QFormLayout()
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Nom d'utilisateur")
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.setPlaceholderText("Mot de passe")
        form.addRow("Utilisateur :", self.input_user)
        form.addRow("Mot de passe :", self.input_pass)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._try_login)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.input_pass.returnPressed.connect(self._try_login)

    def _try_login(self) -> None:
        username = self.input_user.text().strip()
        password = self.input_pass.text()
        if self._auth.login(username, password):
            self.accept()
        else:
            QMessageBox.warning(self, "Authentification échouée", "Identifiants incorrects. Réessayez.")
            self.input_pass.clear()
            self.input_pass.setFocus()
