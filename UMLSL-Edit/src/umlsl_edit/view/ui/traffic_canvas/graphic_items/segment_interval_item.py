from typing import TYPE_CHECKING, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF, Qt
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import (
    CrossingSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import (
    LaneSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import (
    SegmentInterval,
)
from umlsl_edit.view.view_constants import COLORS, DIMENSION, Z_LAYERS

if TYPE_CHECKING:
    from umlsl_edit.model.traffic_value_objects.lane import Lane


class SegmentIntervalItem(QGraphicsItem):
    """Base graphics item for segment intervals.

    This class handles the visualization of different segment intervals on the traffic canvas.
    It supports straight segments as well as corners (crossing segments).
    """

    def __init__(
            self,
            segment_interval: SegmentInterval,
            lane_start: "Lane",
            lane_end: "Lane",
            is_last_interval: bool,
            car: Car,
            application_controller: "ApplicationController",
            is_car_selected: bool = False,
    ) -> None:
        super().__init__()
        self.segment_interval = segment_interval
        self.is_last_interval = is_last_interval
        self.car = car
        self.is_car_selected = bool(is_car_selected)
        self.application_controller = application_controller
        self.lane_start = lane_start
        self.lane_end = lane_end

        self.color = QColor(car.color)
        self.color.setAlphaF(0.5)
        self.brush = QBrush(self.color)
        self.pen = Qt.NoPen

        self._rect = QRectF()
        self._path = QPainterPath()

        self._setup_style()
        self.refresh_geometry()

    @property
    def should_ignore_lane_direction(self) -> bool:
        """Determines if the lane direction should be ignored for global interval calculations."""
        return False

    @property
    def should_extend_car(self) -> bool:
        """Determines if the segment visual should match car width and add car tips."""
        return False

    def _setup_style(self) -> None:
        """Hook for subclasses to override visual styles."""
        pass



    def _update_z_value(self) -> None:
        """Updates the z-value of the item to ensure correct rendering order."""
        self.setZValue(Z_LAYERS.SEGMENT_INTERVAL)

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the item."""
        return self._rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None) -> None:
        """Paints the segment interval on the canvas."""
        self._update_z_value()
        painter.setBrush(self.brush)
        painter.setPen(self.pen)

        if hasattr(self, '_path') and not self._path.isEmpty():
            painter.drawPath(self._path)
        else:
            painter.drawRect(self._rect)

    def refresh_geometry(self) -> None:
        """Recalculates the geometry and path for the segment interval."""
        self.prepareGeometryChange()

        reader = self.application_controller.get_traffic_snapshot_reader()
        x_seg, y_seg = self.segment_interval.segment.get_position(reader)
        width_seg, height_seg = self.segment_interval.segment.get_size(reader)

        global_interval = self.segment_interval.get_global_interval(
            reader, self.car, self.should_ignore_lane_direction
        )

        is_horizontal, is_corner, horizontal_lane, vertical_lane = self._determine_segment_orientation_and_type(reader)

        self._path = QPainterPath()
        self._path.setFillRule(Qt.WindingFill)

        if is_corner:
            self._calculate_corner_geometry(
                x_seg, y_seg, width_seg, height_seg, horizontal_lane, vertical_lane
            )
        else:
            self._calculate_straight_geometry(
                is_horizontal, x_seg, y_seg, width_seg, height_seg, global_interval
            )

        self.update()

    def _determine_segment_orientation_and_type(self, reader) -> Tuple[bool, bool, Optional["Lane"], Optional["Lane"]]:
        """Determines if the segment is horizontal, if it is a corner, and retrieves associated lanes."""
        is_horizontal = True
        is_corner = False
        horizontal_lane = None
        vertical_lane = None

        if isinstance(self.segment_interval.segment, LaneSegment):
            road = reader.get_road_by_uid(self.segment_interval.segment.lane.road_uid)
            is_horizontal = road.orientation == RoadOrientation.HORIZONTAL

        elif isinstance(self.segment_interval.segment, CrossingSegment):
            crossing_segment = self.segment_interval.segment
            horizontal_lane = crossing_segment.horizontal_lane
            vertical_lane = crossing_segment.vertical_lane

            if (
                (horizontal_lane == self.lane_start and vertical_lane == self.lane_end)
                or (horizontal_lane == self.lane_end and vertical_lane == self.lane_start)
            ):
                is_corner = True
            else:
                is_horizontal = horizontal_lane in (self.lane_start, self.lane_end)

        return is_horizontal, is_corner, horizontal_lane, vertical_lane

    def _calculate_corner_geometry(
        self, x_seg: float, y_seg: float, width_seg: float, height_seg: float,
        horizontal_lane: "Lane", vertical_lane: "Lane"
    ) -> None:
        """Calculates the geometry for a corner (crossing) segment."""
        hx, hy = x_seg, y_seg - height_seg
        hw, hh = width_seg, height_seg

        if self.should_extend_car:
            hy += (DIMENSION.LANE_WIDTH - DIMENSION.CAR_WIDTH) / 2
            hh = DIMENSION.CAR_WIDTH

        vx, vy = x_seg, y_seg - height_seg
        vw, vh = width_seg, height_seg

        if self.should_extend_car:
            vx += (DIMENSION.LANE_WIDTH - DIMENSION.CAR_WIDTH) / 2
            vw = DIMENSION.CAR_WIDTH

        ox = max(hx, vx)
        oy = max(hy, vy)
        ow = min(hx + hw, vx + vw) - ox
        oh = min(hy + hh, vy + vh) - oy

        final_hx, final_hy, final_hw, final_hh = hx, hy, hw, hh
        final_vx, final_vy, final_vw, final_vh = vx, vy, vw, vh

        horizontal_is_entry = (self.lane_start == horizontal_lane)
        if self.lane_start != horizontal_lane and self.lane_start != vertical_lane:
            horizontal_is_entry = (self.car.lane.road.orientation == RoadOrientation.HORIZONTAL)

        is_reverse = self.car.speed < 0
        h_moves_right = (horizontal_lane.lane_index >= 0) != is_reverse
        v_moves_down = (vertical_lane.lane_index >= 0) != is_reverse

        if horizontal_is_entry:
            keep_left_arm = h_moves_right
            keep_top_arm = not v_moves_down
        else:
            keep_left_arm = not h_moves_right
            keep_top_arm = v_moves_down

        if keep_left_arm:
            final_hw = (ox + ow) - hx
        else:
            final_hx = ox
            final_hw = (hx + hw) - ox

        if keep_top_arm:
            final_vh = (oy + oh) - vy
        else:
            final_vy = oy
            final_vh = (vy + vh) - oy

        self._path.addRect(QRectF(final_hx, final_hy, final_hw, final_hh))
        self._path.addRect(QRectF(final_vx, final_vy, final_vw, final_vh))
        self._rect = self._path.boundingRect()

    def _calculate_straight_geometry(
        self, is_horizontal: bool, x_seg: float, y_seg: float,
        width_seg: float, height_seg: float, global_interval
    ) -> None:
        """Calculates the geometry for a straight (lane) segment."""
        if is_horizontal:
            x = x_seg + global_interval.start
            width = global_interval.length()
            y = y_seg - height_seg
            height = height_seg
            if self.should_extend_car:
                height = DIMENSION.CAR_WIDTH
                y += (DIMENSION.LANE_WIDTH - DIMENSION.CAR_WIDTH) / 2
        else:
            x = x_seg
            width = width_seg
            y = y_seg - height_seg + global_interval.start
            height = global_interval.length()
            if self.should_extend_car:
                width = DIMENSION.CAR_WIDTH
                x += (DIMENSION.LANE_WIDTH - DIMENSION.CAR_WIDTH) / 2

        if self.is_last_interval and self.should_extend_car:
            self._calculate_tip_geometry(is_horizontal, x, y, width, height)
        else:
            self._rect = QRectF(x, y, width, height)

    def _calculate_tip_geometry(self, is_horizontal: bool, x: float, y: float, width: float, height: float) -> None:
        """Calculates the geometry for the tip of the car when it's the last interval."""
        lane_idx = self.lane_end.lane_index
        is_backward = (lane_idx < 0) != (self.car.speed < 0)
        t = DIMENSION.CAR_TRIANGLE_LENGTH

        if is_horizontal:
            if not is_backward:
                # Moving Right (->)
                poly = QPolygonF([
                    QPointF(x, y),
                    QPointF(x + width - t, y),
                    QPointF(x + width, y + height / 2.0),
                    QPointF(x + width - t, y + height),
                    QPointF(x, y + height)
                ])
            else:
                # Moving Left (<-)
                poly = QPolygonF([
                    QPointF(x + width, y),
                    QPointF(x + width, y + height),
                    QPointF(x + t, y + height),
                    QPointF(x, y + height / 2.0),
                    QPointF(x + t, y)
                ])
            self._path.addPolygon(poly)
        else:
            if not is_backward:
                # Moving Down (v)
                poly = QPolygonF([
                    QPointF(x, y),
                    QPointF(x + width, y),
                    QPointF(x + width, y + height - t),
                    QPointF(x + width / 2.0, y + height),
                    QPointF(x, y + height - t)
                ])
            else:
                # Moving Up (^)
                poly = QPolygonF([
                    QPointF(x, y + height),
                    QPointF(x + width, y + height),
                    QPointF(x + width, y + t),
                    QPointF(x + width / 2.0, y),
                    QPointF(x, y + t)
                ])
            self._path.addPolygon(poly)

        self._rect = self._path.boundingRect()


class PathSegmentItem(SegmentIntervalItem):
    """Visualizes standard path segments."""

    def _setup_style(self) -> None:
        self.pen = QPen(COLORS.TEXT, .04)
        self.pen.setCosmetic(False)
        self.color = QColor(COLORS.TEXT)
        self.color.setAlphaF(0.2)
        self.brush.setColor(self.color)


class ViewSegmentItem(SegmentIntervalItem):
    """Visualizes view lanes with a soft background fill."""

    @property
    def should_ignore_lane_direction(self) -> bool:
        return True

    def _setup_style(self) -> None:
        self.pen = Qt.NoPen
        self.color = QColor(175, 195, 215)
        self.color.setAlphaF(0.25)
        self.brush.setColor(self.color)


class ReservedSegmentItem(SegmentIntervalItem):
    """Visualizes reserved segments, adjusting for car width."""

    def _setup_style(self) -> None:
        if self.is_car_selected:
            self.color.setAlphaF(1.0)
        else:
            self.color.setAlphaF(0.5)
        self.brush.setColor(self.color)

    @property
    def should_extend_car(self) -> bool:
        return True


class ClaimedSegmentItem(SegmentIntervalItem):
    """Visualizes claimed segments using a dashed outline."""

    @property
    def should_ignore_lane_direction(self) -> bool:
        return True

    def _setup_style(self) -> None:
        self.pen = QPen(COLORS.TEXT, .04)
        self.pen.setStyle(Qt.DashLine)
        self.pen.setDashPattern([2, 2])
        self.pen.setCosmetic(False)
        self.color = QColor(self.car.color)
        self.color.setAlphaF(0.4)
        self.brush.setColor(self.color)
