import logging
from typing import TYPE_CHECKING, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsScene, QStyleOptionGraphicsItem, QWidget

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.errors.car_errors import (
    CarTrafficSnapshotContextValidationError,
    CarValidationError,
)
from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import (
    CrossingSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import (
    LaneSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import (
    ViewSegmentIntervall,
)
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection
from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog
from umlsl_edit.view.ui.traffic_canvas.graphic_items.road_item import RoadItem
from umlsl_edit.view.ui.traffic_canvas.graphic_items.segment_interval_item import (
    ClaimedSegmentItem,
    ReservedSegmentItem,
    ViewSegmentItem,
)
from umlsl_edit.view.ui.traffic_canvas.graphic_items.selectable_graphics_item import (
    SelectableGraphicsItem,
)
from umlsl_edit.view.view_constants import COLORS, DIMENSION, Z_LAYERS

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController
    from umlsl_edit.model.traffic_value_objects.lane import Lane

logger = logging.getLogger(__name__)


class CarItemStyle:
    """Contains styling constants for the CarItem."""
    PEN_WIDTH = 0.07
    HOVER_LIGHTNESS = 110
    LABEL_SCALE_THRESHOLD = DIMENSION.GRID_FINE_THRESHOLD


class CarItem(SelectableGraphicsItem):
    """
    Represents a car entity on the traffic canvas.
    Handles the visualization of the car, its movement, and its associated segment intervals (claimed, reserved, view).
    """

    def __init__(
            self,
            car: Car,
            road_item: RoadItem,
            application_controller: "ApplicationController",
    ) -> None:
        super().__init__(application_controller)

        self._car = car
        self._road_item = road_item
        self._road = road_item.data(0)

        self._segments = []

        self._polygon = QPolygonF()
        self._body_brush = QBrush()
        self._body_pen = QPen()

        self._road_item.add_position_listener(self)
        self.update_data(car)

    def cleanup(self) -> None:
        """Cleans up listeners and removes segments from the scene before deletion."""
        if self._road_item:
            self._road_item.remove_position_listener(self)
        self._clear_segments()

    def update_data(self, car: Car, road_item: Optional[RoadItem] = None) -> None:
        """Updates the internal data of the car, potentially swapping to a new road item."""
        self._car = car
        self.setData(0, car)

        if road_item is not None and road_item != self._road_item:
            self._road_item.remove_position_listener(self)
            self._road_item = road_item
            self._road = road_item.data(0)
            self._road_item.add_position_listener(self)

        if self._road_item:
            self._road = self._road_item.data(0)

        self.refresh_geometry()

    def update_segments(self) -> None:
        """Refreshes the visualization of claimed, reserved, and view segments."""
        self._clear_segments()

        if self.is_selected:
            self._add_view_segment_items()

        self._add_segment_items(self._car.environment.reserved, ReservedSegmentItem)
        self._add_segment_items(self._car.environment.claimed, ClaimedSegmentItem)

    def _add_view_segment_items(self) -> None:
        """Adds graphical items representing the car's view segments (virtual lanes)."""
        parallel_virtual_lanes = self._car.environment.parallel_virtual_lanes
        if not parallel_virtual_lanes:
            return

        seen = set()
        for parallel_virtual_lane in parallel_virtual_lanes:
            for virtual_lane in parallel_virtual_lane:
                view_intervals = self._to_view_segment_intervals(virtual_lane.segment_intervals)
                self._add_segment_items(view_intervals, ViewSegmentItem, seen)

    def _to_view_segment_intervals(self, segment_intervals) -> list[ViewSegmentIntervall]:
        """Converts standard segment intervals to ViewSegmentIntervall objects with offsets."""
        view_intervals = []
        offset = 0.0
        path_segments = tuple(seg_interval.segment for seg_interval in segment_intervals)
        for seg_interval in segment_intervals:
            view_intervals.append(
                ViewSegmentIntervall(seg_interval.segment, seg_interval.interval, offset, path_segments)
            )
            offset = seg_interval.interval.end
        return view_intervals

    def _clear_segments(self) -> None:
        """Removes all currently displayed segment items associated with this car."""
        scene = self._get_scene()
        if scene is None:
            self._segments.clear()
            return
        for seg in self._segments:
            scene.removeItem(seg)
        self._segments.clear()

    def _add_segment_items(self, segments, segment_class, seen=None) -> None:
        """
        Instantiates and adds segment items to the scene.

        Args:
            segments: List of segment data objects.
            segment_class: The class to instantiate for each segment.
            seen: Set of already rendered segment intervals to prevent duplicates.
        """
        scene = self._get_scene()
        if scene is None or not segments:
            return

        if seen is None:
            seen = set()

        for i, seg_data in enumerate(segments):
            segment = seg_data.segment
            start = seg_data.interval.start if self._car.next_turn is None or self._car.next_turn.direction == TurnDirection.STRAIGHT else 0

            if isinstance(segment, LaneSegment):
                seg_id = (segment.lane.lane_index, segment.lane.road_uid, start
                          )
            elif isinstance(segment, CrossingSegment):
                seg_id = (segment.horizontal_lane.road_uid, segment.vertical_lane.road_uid,
                          segment.vertical_lane.lane_index, segment.horizontal_lane.lane_index,
                          start)

            if seg_id in seen:
                continue
            seen.add(seg_id)

            entry_lane, exit_lane = self._determine_entry_and_exit_lanes(segments, i)

            if not self._validate_segment_road(seg_data.segment):
                continue

            seg_item = segment_class(
                segment_interval=seg_data,
                lane_start=entry_lane,
                lane_end=exit_lane,
                application_controller=self.application_controller,
                car=self._car,
                is_last_interval=(i == len(segments) - 1),
                is_car_selected=self.is_selected,
            )
            scene.addItem(seg_item)
            self._segments.append(seg_item)

    def _determine_entry_and_exit_lanes(self, segments, current_index: int) -> Tuple["Lane", "Lane"]:
        """Finds the closest preceding lane for entry and closest succeeding lane for exit."""
        entry_lane = None
        exit_lane = None

        # Find the closest preceding lane for entry
        for j in range(current_index, -1, -1):
            if hasattr(segments[j].segment, 'lane'):
                entry_lane = segments[j].segment.lane
                break

        # Find the closest succeeding lane for exit
        for j in range(current_index, len(segments)):
            if hasattr(segments[j].segment, 'lane'):
                exit_lane = segments[j].segment.lane
                break

        if entry_lane is None:
            entry_lane = self._car.lane
        if exit_lane is None:
            exit_lane = entry_lane

        return entry_lane, exit_lane

    def _validate_segment_road(self, segment) -> bool:
        """Checks if the road associated with the segment exists in the traffic snapshot."""
        road_uid = ""
        try:
            reader = self.application_controller.get_traffic_snapshot_reader()
            if isinstance(segment, LaneSegment):
                road_uid = segment.lane.road_uid
                reader.get_road_by_uid(road_uid)
            elif isinstance(segment, CrossingSegment):
                road_uid = segment.vertical_lane.road_uid
                reader.get_road_by_uid(road_uid)
                road_uid = segment.horizontal_lane.road_uid
                reader.get_road_by_uid(road_uid)
            return True
        except ValueError:
            logger.warning(f"Skipping segment interval for non-existent road uid: {road_uid}")
            return False

    def _get_scene(self) -> QGraphicsScene | None:
        return self.scene()

    def _get_constraint_for_orientation(self, orientation: RoadOrientation) -> int:
        """Returns the movement constraint (X or Y only) based on road orientation."""
        if orientation == RoadOrientation.HORIZONTAL:
            return SelectableGraphicsItem.AXIS_X_ONLY
        return SelectableGraphicsItem.AXIS_Y_ONLY

    def _update_styles(self) -> None:
        """Updates the visual styling of the car (z-value, colors, pens)."""
        self.setZValue(Z_LAYERS.SELECTED_CAR if self.is_selected else Z_LAYERS.CAR)

        constraint = self._get_constraint_for_orientation(self._road.orientation)
        self.set_movement_constraint(constraint)

        car_color = QColor(self._car.color)
        if self.is_hovered:
            car_color = car_color.lighter(CarItemStyle.HOVER_LIGHTNESS)

        border_color = COLORS.TEXT if self.is_selected else COLORS.TRANSPARENT
        self._body_brush = QBrush(car_color)
        self._body_pen = QPen(border_color, CarItemStyle.PEN_WIDTH)

    def on_selection_changed(self, is_selected: bool) -> None:
        self._update_styles()
        self.update_segments()
        self.update()

    def on_hover_changed(self, is_hovered: bool) -> None:
        self._update_styles()
        self.update()

    def on_move_committed(self, delta_x: float, delta_y: float) -> None:
        """Handles committing the car's movement to the application controller."""
        is_horiz = self._road.orientation == RoadOrientation.HORIZONTAL
        delta = delta_x if is_horiz else delta_y
        new_position = self._car.position_on_lane + delta

        try:
            self.application_controller.command_controller.edit_car(
                car=self._car,
                position_on_lane=new_position,
            )
        except (CarValidationError, CarTrafficSnapshotContextValidationError) as e:
            view = self.scene().views()[0] if self.scene().views() else None
            WarningDialog("Cannot move car", str(e), view).exec()

    def boundingRect(self) -> QRectF:
        return self._polygon.boundingRect()

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionGraphicsItem,
            widget: Optional[QWidget] = None,
    ) -> None:
        painter.setPen(self._body_pen)
        painter.setBrush(self._body_brush)
        painter.drawPolygon(self._polygon)
        self._paint_label(painter, option)

    def _paint_label(self, painter: QPainter, option: QStyleOptionGraphicsItem) -> None:
        """Paints the car's name label centered on the car polygon if zoomed in enough."""
        transform = painter.worldTransform()
        lod = option.levelOfDetailFromTransform(transform)

        if lod <= CarItemStyle.LABEL_SCALE_THRESHOLD:
            return

        text_scale = 1.0 / lod
        painter.save()

        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(COLORS.BACKGROUND)

        center = self._polygon.boundingRect().center()
        painter.translate(center.x(), center.y())
        painter.scale(text_scale, -text_scale)

        text = str(self._car.name)
        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(text)

        painter.drawText(
            -text_rect.width() / 2,
            text_rect.height() / 4,
            text
        )
        painter.restore()

    def refresh_geometry(self) -> None:
        """
        Recalculates polygon.
        Anchor: car.position_on_lane corresponds to the BACK of the car.
        """
        self._update_styles()
        self.prepareGeometryChange()

        # Extract basic values
        car = self._car
        road = self._road
        is_vertical = road.orientation == RoadOrientation.VERTICAL

        # Calculate polygon points
        points = self._calculate_local_points()
        poly_points = self._transform_points_to_world(points, car, road, is_vertical)

        self._polygon = QPolygonF(poly_points)
        self.update()

    def _calculate_local_points(self) -> list[QPointF]:
        """Defines the local car shape with the rear anchored at (0, 0)."""
        l = self._car.length
        w = DIMENSION.CAR_WIDTH / 2.0
        t = DIMENSION.CAR_TRIANGLE_LENGTH

        return [
            QPointF(0, -w),  # Back-Right
            QPointF(l - t, -w),  # Shoulder-Right
            QPointF(l, 0),  # Tip
            QPointF(l - t, w),  # Shoulder-Left
            QPointF(0, w)  # Back-Left
        ]

    def _transform_points_to_world(self, points: list[QPointF], car: Car, road, is_vertical: bool) -> list[QPointF]:
        """Transforms local car points into world coordinates based on lane and position."""
        lane_idx = car.lane.lane_index
        is_backward = (lane_idx < 0) != (car.speed < 0)
        lane_w = DIMENSION.LANE_WIDTH

        # Determine lateral direction/offset logic
        vert_mod = 1 if is_vertical else -1
        center_offset = (lane_idx * lane_w * vert_mod) + (lane_w / 2.0 * vert_mod)

        # Apply transition offset if changing lanes
        if car.environment.claimed:
            center_offset += car.transition * lane_w

        road_base = road.position + (self._road_item.x() if is_vertical else self._road_item.y())
        lat_pos = road_base + center_offset
        long_pos = car.position_on_lane

        # Transform local points
        poly_points = []
        for p in points:
            # If backward lane, flip longitudinal direction (face negative)
            lx = -p.x() if is_backward else p.x()
            ly = p.y()

            if is_vertical:
                poly_points.append(QPointF(lat_pos + ly, long_pos + lx))
            else:
                poly_points.append(QPointF(long_pos + lx, lat_pos + ly))

        return poly_points
