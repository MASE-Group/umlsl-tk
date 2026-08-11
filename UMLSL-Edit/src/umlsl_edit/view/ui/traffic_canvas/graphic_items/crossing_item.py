"""
Crossing graphics item for the UMLSL Traffic Editor.

Provides a visual representation of the intersection area between two
perpendicular roads, including a background and lane grid.
"""

from typing import Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from umlsl_edit.model.entities.road import Road, RoadOrientation
from umlsl_edit.view.ui.traffic_canvas.graphic_items.road_item import RoadItem
from umlsl_edit.view.view_constants import COLORS, DIMENSION, Z_LAYERS


class CrossingItemStyle:
    """Constants and styling configuration for the CrossingItem."""
    PEN_WIDTH = DIMENSION.LINE_WIDTH_CROSSING_SEGMENT

    # Dash pattern: [dash_length, gap_length] relative to pen width
    # 0.05 / width results in very small dots/dashes appropriate for this scale
    DASH_PATTERN = [
        0.05 / DIMENSION.LINE_WIDTH_CROSSING_SEGMENT,
        0.1 / DIMENSION.LINE_WIDTH_CROSSING_SEGMENT
    ]


class CrossingItem(QGraphicsItem):
    """
    Graphics item representing the intersection of two perpendicular roads.

    Displays a rectangular crossing area with a lane grid overlay.
    It automatically registers itself as a listener to the connected roads
    to update geometry when they move.
    """

    def __init__(self, road_1: RoadItem, road_2: RoadItem) -> None:
        """
        Initialize the crossing item between two roads.

        Args:
            road_1: The first road item.
            road_2: The second road item (must be perpendicular to road_1).
        """
        super().__init__()

        self._road_a = road_1
        self._road_b = road_2
        self._rect = QRectF()

        # Graphic resources

        grid_color = QColor(255, 255, 255, 127)

        self._grid_pen = QPen(grid_color, CrossingItemStyle.PEN_WIDTH)
        self._grid_pen.setStyle(Qt.DashLine)
        self._grid_pen.setDashPattern(CrossingItemStyle.DASH_PATTERN)

        # Register listeners for road position updates.
        self._road_a.add_position_listener(self)
        self._road_b.add_position_listener(self)

        # Initial geometry calculation.
        self.refresh_geometry()

    def cleanup(self) -> None:
        """
        Disconnects listeners.
        Must be called by the Scene before removing this item.
        """
        if self._road_a:
            self._road_a.remove_position_listener(self)
        if self._road_b:
            self._road_b.remove_position_listener(self)

    # -------------------------------------------------------------------------
    # Visual State
    # -------------------------------------------------------------------------

    def _update_z_value(self) -> None:
        """Update the Z-order based on selection state of connected roads."""
        is_selected = self._road_a.is_selected or self._road_b.is_selected
        self.setZValue(Z_LAYERS.SELECTED_CROSSING if is_selected else Z_LAYERS.CROSSING)

    def _get_brush_color(self) -> QBrush:
        """Returns background color based on selection state."""
        is_selected = self._road_a.is_selected or self._road_b.is_selected
        color = COLORS.LAYER.lighter() if is_selected else COLORS.LAYER
        return QBrush(color)

    # -------------------------------------------------------------------------
    # Graphics Interface (Qt)
    # -------------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        return self._rect

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionGraphicsItem,
            widget: Optional[QWidget] = None,
    ) -> None:
        self._update_z_value()

        # Background
        painter.setBrush(self._get_brush_color())
        painter.setPen(Qt.NoPen)
        painter.drawRect(self._rect)

        # Grid
        painter.setPen(self._grid_pen)
        self._draw_grid(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        """Draws the lane grid lines."""
        lane_width = DIMENSION.LANE_WIDTH

        # Draw Vertical Lines
        self._draw_lines(
            painter,
            start_val=self._rect.left(),
            end_val=self._rect.right(),
            fixed_start=self._rect.top(),
            fixed_end=self._rect.bottom(),
            step=lane_width,
            is_vertical=True
        )

        # Draw Horizontal Lines
        self._draw_lines(
            painter,
            start_val=self._rect.top(),
            end_val=self._rect.bottom(),
            fixed_start=self._rect.left(),
            fixed_end=self._rect.right(),
            step=lane_width,
            is_vertical=False
        )

    def _draw_lines(
            self,
            painter: QPainter,
            start_val: float,
            end_val: float,
            fixed_start: float,
            fixed_end: float,
            step: float,
            is_vertical: bool
    ) -> None:
        """Generic method to draw parallel lines across the rect."""
        current = start_val
        # Use epsilon to prevent floating point errors skipping the last line
        limit = end_val + 0.001

        while current <= limit:
            if is_vertical:
                p1 = QPointF(current, fixed_start)
                p2 = QPointF(current, fixed_end)
            else:
                p1 = QPointF(fixed_start, current)
                p2 = QPointF(fixed_end, current)

            painter.drawLine(p1, p2)
            current += step

    # -------------------------------------------------------------------------
    # Geometry Calculation (Listener Implementation)
    # -------------------------------------------------------------------------

    def refresh_geometry(self) -> None:
        """
        Recalculate the crossing rectangle based on current road positions.
        Called by RoadItem via the GeometryListener protocol.
        """
        self.prepareGeometryChange()
        self._rect = self._calculate_intersection_rect()
        self.update()

    def _calculate_intersection_rect(self) -> QRectF:
        """Calculate the intersection area of the two roads."""
        h_road, v_road = self._identify_road_orientations()

        # Calculate bounds in scene coordinates
        y_pos, height = self._get_road_transverse_bounds(h_road, is_horizontal=True)
        x_pos, width = self._get_road_transverse_bounds(v_road, is_horizontal=False)

        return QRectF(x_pos, y_pos, width, height)

    def _identify_road_orientations(self) -> Tuple[RoadItem, RoadItem]:
        """Returns (Horizontal_Item, Vertical_Item)."""
        if self._road_a.data(0).orientation == RoadOrientation.HORIZONTAL:
            return self._road_a, self._road_b
        return self._road_b, self._road_a

    def _get_road_transverse_bounds(
            self,
            item: RoadItem,
            is_horizontal: bool
    ) -> Tuple[float, float]:
        """
        Calculates the start position and total width of the road
        perpendicular to its travel direction.
        """
        road: Road = item.data(0)
        lane_width = DIMENSION.LANE_WIDTH

        total_lanes = road.number_of_forward_lanes + road.number_of_backward_lanes
        total_thickness = total_lanes * lane_width

        # Based on RoadItem geometry logic:
        # Horiz: Top = Pos - (ForwardLanes * Width)
        # Vert:  Left = Pos - (BackwardLanes * Width)
        if is_horizontal:
            offset = road.number_of_forward_lanes * lane_width
            start_pos = road.position - offset + item.y()
        else:
            offset = road.number_of_backward_lanes * lane_width
            start_pos = road.position - offset + item.x()

        return start_pos, total_thickness
