"""
Real-time graph view for the Child (Sentinel).
Extends the Parent canvas with animated blinking for anomalous nodes.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen, QFont
from PyQt6.QtWidgets import QWidget

from digital_twin_factory.shared_logic.models import GraphNode, NodeType, StepStatus, TwinModel


_NODE_W = 160
_NODE_H = 50

_STATUS_COLORS = {
    StepStatus.OK:      QColor("#238636"),
    StepStatus.WARNING: QColor("#d29922"),
    StepStatus.ERROR:   QColor("#f85149"),
    StepStatus.RUNNING: QColor("#1f6feb"),
    StepStatus.IDLE:    QColor("#21262d"),
}

_TYPE_ACCENT = {
    NodeType.HUMAN:     QColor("#1f6feb"),
    NodeType.AUTOMATED: QColor("#238636"),
    NodeType.DECISION:  QColor("#d29922"),
    NodeType.START:     QColor("#3fb950"),
    NodeType.END:       QColor("#f85149"),
}


class SentinelGraphView(QWidget):
    """
    Live graph canvas with:
    - Status-coloured node fill
    - Red blinking ring for ERROR nodes
    - Yellow blinking ring for WARNING nodes
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(700, 450)
        self._model: Optional[TwinModel] = None
        self._blink_state = True

        # Blink timer at 500ms
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(500)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start()

    # ------------------------------------------------------------------
    def set_model(self, model: TwinModel) -> None:
        self._model = model
        self._auto_layout()
        self.update()

    def _auto_layout(self) -> None:
        if not self._model:
            return
        if all(n.position_x == 0.0 and n.position_y == 0.0 for n in self._model.nodes):
            import math
            cols = max(1, math.ceil(math.sqrt(len(self._model.nodes))))
            for idx, node in enumerate(self._model.nodes):
                node.position_x = 30 + (idx % cols) * 210
                node.position_y = 30 + (idx // cols) * 120

    def _toggle_blink(self) -> None:
        self._blink_state = not self._blink_state
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, _event) -> None:  # type: ignore[override]
        if not self._model:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d1117"))

        node_map = {n.id: n for n in self._model.nodes}

        # Edges
        for edge in self._model.edges:
            src = node_map.get(edge.source_id)
            tgt = node_map.get(edge.target_id)
            if src and tgt:
                sx, sy = src.position_x + _NODE_W / 2, src.position_y + _NODE_H / 2
                tx, ty = tgt.position_x + _NODE_W / 2, tgt.position_y + _NODE_H / 2
                painter.setPen(QPen(QColor("#30363d"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(int(sx), int(sy), int(tx), int(ty))

        # Nodes
        for node in self._model.nodes:
            self._draw_node(painter, node)

        painter.end()

    def _draw_node(self, p: QPainter, node: GraphNode) -> None:
        rect = QRectF(node.position_x, node.position_y, _NODE_W, _NODE_H)
        fill_color = _STATUS_COLORS.get(node.status, QColor("#21262d"))
        accent = _TYPE_ACCENT.get(node.node_type, QColor("#30363d"))

        # Background
        p.setPen(QPen(accent, 1))
        p.setBrush(QBrush(fill_color.darker(200)))
        p.drawRoundedRect(rect, 8, 8)

        # Blinking ring for anomalies
        if node.status in (StepStatus.ERROR, StepStatus.WARNING):
            ring_color = _STATUS_COLORS[node.status]
            if self._blink_state:
                ring_pen = QPen(ring_color, 3)
            else:
                ring_pen = QPen(ring_color.darker(300), 1)
            p.setPen(ring_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 8, 8)

        # Status dot
        dot_color = _STATUS_COLORS.get(node.status, QColor("#30363d"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(dot_color))
        p.drawEllipse(int(rect.right() - 14), int(rect.top() + 6), 8, 8)

        # Label
        p.setPen(QColor("#c9d1d9"))
        font = QFont("Consolas", 9)
        font.setBold(True)
        p.setFont(font)
        label = node.label if len(node.label) <= 18 else node.label[:16] + "…"
        p.drawText(rect.adjusted(4, 0, -16, 0), Qt.AlignmentFlag.AlignCenter, label)

        # Duration badge (if SLA present)
        if node.sla:
            badge_font = QFont("Consolas", 7)
            p.setFont(badge_font)
            p.setPen(QColor("#8b949e"))
            badge_rect = QRectF(rect.left(), rect.bottom() + 2, _NODE_W, 12)
            sla_txt = f"SLA {node.sla.max_duration_seconds:.0f}s"
            p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, sla_txt)
