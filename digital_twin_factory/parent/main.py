"""Entry point for the Digital Twin Factory — Parent (Builder) application."""
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from digital_twin_factory.parent.ui.main_window import ParentMainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Digital Twin Factory — Builder")
    app.setOrganizationName("VorpalEx")

    window = ParentMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
