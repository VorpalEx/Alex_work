"""Shared dark-mode industrial stylesheet for both Parent and Child UIs."""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #161b22;
}

QTabBar::tab {
    background-color: #21262d;
    color: #8b949e;
    padding: 8px 18px;
    border: 1px solid #30363d;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #161b22;
    color: #58a6ff;
    border-bottom: 2px solid #58a6ff;
}

QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 14px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #58a6ff;
    color: #58a6ff;
}

QPushButton:pressed {
    background-color: #1f6feb;
    color: #ffffff;
}

QPushButton#build_btn {
    background-color: #238636;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 10px 20px;
    border-color: #2ea043;
}

QPushButton#build_btn:hover {
    background-color: #2ea043;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #1f6feb;
}

QLineEdit:focus, QTextEdit:focus {
    border-color: #58a6ff;
}

QLabel {
    color: #c9d1d9;
}

QLabel#section_title {
    color: #58a6ff;
    font-size: 14px;
    font-weight: bold;
}

QLabel#status_ok {
    color: #3fb950;
    font-weight: bold;
}

QLabel#status_error {
    color: #f85149;
    font-weight: bold;
}

QLabel#status_warning {
    color: #d29922;
    font-weight: bold;
}

QGroupBox {
    border: 1px solid #30363d;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
    color: #8b949e;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #8b949e;
}

QTableWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    gridline-color: #21262d;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
}

QTableWidget::item:alternate {
    background-color: #161b22;
}

QHeaderView::section {
    background-color: #21262d;
    color: #8b949e;
    border: 1px solid #30363d;
    padding: 4px 8px;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #0d1117;
    width: 10px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #30363d;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #58a6ff;
}

QProgressBar {
    border: 1px solid #30363d;
    border-radius: 4px;
    background-color: #0d1117;
    text-align: center;
    color: #c9d1d9;
}

QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 3px;
}

QComboBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 4px 8px;
}

QComboBox QAbstractItemView {
    background-color: #21262d;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
}

QSplitter::handle {
    background-color: #30363d;
}
"""
