"""
Interactive graph view panel (Parent).
Renders the TwinModel dependency graph using PyQt6 + QPainter.
Supports node selection, drag, and right-click context menu.
"""
from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...shared_logic.models import GraphNode, NodeType, StepStatus, TwinModel


_NODE_W = 160
_NODE_H = 50
_COLORS = {
    NodeType.HUMAN: QColor("#1f6feb"),
    NodeType.AUTOMATED: QColor("#238636"),
    NodeType.DECISION: QColor("#d29922"),
    NodeType.START: QColor("#3fb950"),
    NodeType.END: QColor("#f85149"),
}
_STATUS_RING = {
    StepStatus.OK: QColor("#3fb950"),
    StepStatus.WARNING: QColor("#d29922"),
    StepStatus.ERROR: QColor("#f85149"),
    StepStatus.RUNNING: QColor("#58a6ff"),
    StepStatus.IDLE: QColor("#30363d"),
}


class _GraphCanvas(QWidget):
    node_selected = pyqtSignal(str)   # node_id

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self._model: Optional[TwinModel] = None
        self._selected_id: Optional[str] = None
        self._drag_id: Optional[str] = None
        self._drag_offset = QPointF(0, 0)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    # ------------------------------------------------------------------
    def set_model(self, model: TwinModel) -> None:
        self._model = model
        self._auto_layout()
        self.update()

    def refresh(self) -> None:
        self.update()

    # ------------------------------------------------------------------
    def _auto_layout(self) -> None:
        """Assign positions if all nodes are at (0, 0)."""
        if not self._model:
            return
        if all(n.position_x == 0.0 and n.position_y == 0.0 for n in self._model.nodes):
            cols = max(1, math.ceil(math.sqrt(len(self._model.nodes))))
            for idx, node in enumerate(self._model.nodes):
                node.position_x = 40 + (idx % cols) * 200
                node.position_y = 40 + (idx // cols) * 120

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:  # type: ignore[override]
        if not self._model:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d1117"))

        node_map = {n.id: n for n in self._model.nodes}

        # Draw edges first
        pen_edge = QPen(QColor("#30363d"), 2)
        painter.setPen(pen_edge)
        for edge in self._model.edges:
            src = node_map.get(edge.source_id)
            tgt = node_map.get(edge.target_id)
            if src and tgt:
                sx = src.position_x + _NODE_W / 2
                sy = src.position_y + _NODE_H / 2
                tx = tgt.position_x + _NODE_W / 2
                ty = tgt.position_y + _NODE_H / 2
                self._draw_arrow(painter, sx, sy, tx, ty, edge.label)

        # Draw nodes
        for node in self._model.nodes:
            self._draw_node(painter, node)

        painter.end()

    def _draw_arrow(self, p: QPainter, x1: float, y1: float, x2: float, y2: float, label: str) -> None:
        pen = QPen(QColor("#58a6ff"), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Arrowhead
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_size = 10
        p.setBrush(QBrush(QColor("#58a6ff")))
        p.setPen(Qt.PenStyle.NoPen)
        path = QPainterPath()
        path.moveTo(QPointF(x2, y2))
        path.lineTo(
            QPointF(x2 - arrow_size * math.cos(angle - 0.4), y2 - arrow_size * math.sin(angle - 0.4))
        )
        path.lineTo(
            QPointF(x2 - arrow_size * math.cos(angle + 0.4), y2 - arrow_size * math.sin(angle + 0.4))
        )
        path.closeSubpath()
        p.drawPath(path)

        if label:
            p.setPen(QColor("#8b949e"))
            mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
            p.drawText(QPointF(mid_x, mid_y), label)

    def _draw_node(self, p: QPainter, node: GraphNode) -> None:
        rect = QRectF(node.position_x, node.position_y, _NODE_W, _NODE_H)
        color = _COLORS.get(node.node_type, QColor("#21262d"))

        # Selection highlight
        if node.id == self._selected_id:
            sel_pen = QPen(QColor("#f0f6fc"), 3)
            p.setPen(sel_pen)
        else:
            p.setPen(QPen(QColor("#30363d"), 1))

        p.setBrush(QBrush(color.darker(180)))
        p.drawRoundedRect(rect, 8, 8)

        # Status ring
        ring_color = _STATUS_RING.get(node.status, QColor("#30363d"))
        p.setPen(QPen(ring_color, 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)

        # Label
        p.setPen(QColor("#c9d1d9"))
        font = QFont("Consolas", 9)
        font.setBold(True)
        p.setFont(font)
        label = node.label if len(node.label) <= 20 else node.label[:18] + "…"
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

        # Node type badge
        badge_font = QFont("Consolas", 7)
        p.setFont(badge_font)
        p.setPen(color.lighter(140))
        badge_rect = QRectF(rect.left(), rect.top() - 16, _NODE_W, 14)
        p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"[{node.node_type.value.upper()}]")

    # ------------------------------------------------------------------
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if not self._model:
            return
        pos = event.position()
        for node in self._model.nodes:
            rect = QRectF(node.position_x, node.position_y, _NODE_W, _NODE_H)
            if rect.contains(pos):
                self._selected_id = node.id
                self._drag_id = node.id
                self._drag_offset = QPointF(pos.x() - node.position_x, pos.y() - node.position_y)
                self.node_selected.emit(node.id)
                self.update()
                return
        self._selected_id = None
        self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_id and self._model:
            node = next((n for n in self._model.nodes if n.id == self._drag_id), None)
            if node:
                pos = event.position()
                node.position_x = pos.x() - self._drag_offset.x()
                node.position_y = pos.y() - self._drag_offset.y()
                self.update()

    def mouseReleaseEvent(self, _event) -> None:  # type: ignore[override]
        self._drag_id = None

    def _context_menu(self, pos) -> None:
        menu = QMenu(self)
        act_add = menu.addAction("Ajouter un nœud")
        result = menu.exec(self.mapToGlobal(pos))
        # Parent window handles actual node creation via signal chain


class GraphViewPanel(QWidget):
    """Hosts the canvas + a node detail sidebar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._model: Optional[TwinModel] = None
        self._build_ui()

    def set_model(self, model: TwinModel) -> None:
        self._model = model
        self.canvas.set_model(model)
        self._update_stats()

    def refresh(self) -> None:
        self.canvas.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        # Canvas
        self.canvas = _GraphCanvas()
        self.canvas.node_selected.connect(self._on_node_selected)
        root.addWidget(self.canvas, 3)

        # Sidebar
        sidebar = QVBoxLayout()
        grp_stats = QGroupBox("Statistiques du graphe")
        v_stats = QVBoxLayout(grp_stats)
        self.lbl_nodes = QLabel("Nœuds : 0")
        self.lbl_edges = QLabel("Arêtes : 0")
        self.lbl_human = QLabel("Étapes humaines : 0")
        self.lbl_auto = QLabel("Étapes automatisées : 0")
        for lbl in (self.lbl_nodes, self.lbl_edges, self.lbl_human, self.lbl_auto):
            v_stats.addWidget(lbl)
        sidebar.addWidget(grp_stats)

        grp_node = QGroupBox("Nœud sélectionné")
        v_node = QVBoxLayout(grp_node)
        self.lbl_node_id = QLabel("ID : —")
        self.lbl_node_label = QLabel("Libellé : —")
        self.lbl_node_type = QLabel("Type : —")
        self.lbl_node_sla = QLabel("SLA : —")
        self.lbl_node_saas = QLabel("SaaS : —")
        for lbl in (self.lbl_node_id, self.lbl_node_label, self.lbl_node_type, self.lbl_node_sla, self.lbl_node_saas):
            v_node.addWidget(lbl)
        sidebar.addWidget(grp_node)
        sidebar.addStretch()
        root.addLayout(sidebar, 1)

    # ------------------------------------------------------------------
    def _update_stats(self) -> None:
        if not self._model:
            return
        self.lbl_nodes.setText(f"Nœuds : {len(self._model.nodes)}")
        self.lbl_edges.setText(f"Arêtes : {len(self._model.edges)}")
        human = sum(1 for n in self._model.nodes if n.node_type.value == "human")
        auto = len(self._model.nodes) - human
        self.lbl_human.setText(f"Étapes humaines : {human}")
        self.lbl_auto.setText(f"Étapes automatisées : {auto}")

    def _on_node_selected(self, node_id: str) -> None:
        if not self._model:
            return
        node = next((n for n in self._model.nodes if n.id == node_id), None)
        if not node:
            return
        self.lbl_node_id.setText(f"ID : {node.id[:8]}…")
        self.lbl_node_label.setText(f"Libellé : {node.label}")
        self.lbl_node_type.setText(f"Type : {node.node_type.value}")
        sla_txt = f"{node.sla.max_duration_seconds:.0f}s" if node.sla else "—"
        self.lbl_node_sla.setText(f"SLA max : {sla_txt}")
        saas_txt = node.saas_provider.value if node.saas_provider else "—"
        self.lbl_node_saas.setText(f"SaaS : {saas_txt} / {node.saas_module_id or '—'}")
