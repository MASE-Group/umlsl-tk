"""
Outline of the world extent on the traffic canvas.

The canvas is unbounded, but the lanes end at the world extent the model computes: around every road, crossing and car
environment, plus the view horizon. The outline shows where, which is also the canvas the scenario gets in UMLSL-Sim.
"""
from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from umlsl_edit.view.view_constants import COLORS, DIMENSION, Z_LAYERS


class WorldBoundaryItem(QGraphicsItem):
    """A dashed rectangle around the world. It takes no part in hit testing, so clicks fall through to the canvas."""

    def __init__(self, half_width: float, half_height: float) -> None:
        super().__init__()
        self._rect = QRectF()
        color = QColor(COLORS.TEXT)
        color.setAlpha(140)
        self._pen = QPen(color, DIMENSION.LINE_WIDTH_WORLD_BOUNDARY, Qt.DashLine)
        self._pen.setCosmetic(True)
        self.setZValue(Z_LAYERS.OVERLAY)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setAcceptHoverEvents(False)
        self.set_extent(half_width, half_height)

    def set_extent(self, half_width: float, half_height: float) -> None:
        self.prepareGeometryChange()
        self._rect = QRectF(-half_width, -half_height, 2 * half_width, 2 * half_height)
        self.update()

    def boundingRect(self) -> QRectF:
        # a cosmetic pen is a few pixels wide whatever the zoom; the margin is in scene units, so keep it small but
        # nonzero, and let a full viewport update (the view's mode) redraw the rest
        return self._rect.adjusted(-0.5, -0.5, 0.5, 0.5)

    def shape(self) -> QPainterPath:
        # no shape: QGraphicsView.itemAt never returns the outline, so clicking empty canvas inside the world still
        # deselects, and dragging still pans
        return QPainterPath()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        painter.setPen(self._pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._rect)
