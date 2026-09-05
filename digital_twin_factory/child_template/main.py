"""
Entry point for the Digital Twin Sentinel (Child) application.
Reads config.json from the same directory (injected by the Builder at build time).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

# Support both PyInstaller bundle and development run
_HERE = Path(__file__).resolve().parent
_CONFIG = _HERE / "config.json"


def _load_model():
    """Load TwinModel from the embedded config.json."""
    # Add project root to sys.path for dev mode
    _root = _HERE.parents[2]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    from digital_twin_factory.shared_logic.graph_schema import twin_from_dict

    if not _CONFIG.exists():
        raise FileNotFoundError(f"config.json introuvable dans : {_HERE}")
    data = json.loads(_CONFIG.read_text(encoding="utf-8"))
    return twin_from_dict(data)


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Digital Twin Sentinel")
    app.setOrganizationName("VorpalEx")

    try:
        model = _load_model()
    except Exception as exc:
        QMessageBox.critical(None, "Erreur de démarrage", str(exc))
        sys.exit(1)

    from digital_twin_factory.child_template.ui.main_window import SentinelMainWindow
    window = SentinelMainWindow(model)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
