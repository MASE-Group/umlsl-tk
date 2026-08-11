from dataclasses import dataclass
from typing import TYPE_CHECKING

from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import (
    CrossingSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import Car


@dataclass(frozen=True)
class SegmentInterval:
    """
    Represents a segment interval on the virtual lane of the car.
    """
    segment: Segment
    interval: Interval

    def get_global_interval(self, ts: TrafficSnapshotReader, car: "Car",
                            should_ignore_lane_direction: bool = False) -> Interval:
        """
        The interval stored as a property in this class is purely relative to the segment and the path direction.
        This function converts the interval to a global interval. That means adding the target coordinate of the
        segment's start position to the interval yields the interval with global coordinates. (Target means for horizontal
        lanes it is the x position, for vertical lanes it is the y position.)
        """

        if isinstance(self.segment, CrossingSegment):
            return self.interval

        road = ts.get_road_by_uid(self.segment.lane.road_uid)

        def direction_from_path():
            if getattr(car, "environment", None) is None:
                return None
            path_segments = getattr(car.environment, "path", None)
            if not path_segments:
                return None

            target_road_uid = self.segment.lane.road_uid
            reference_index = None
            for i, seg in enumerate(path_segments):
                if seg == self.segment:
                    reference_index = i
                    break
            if reference_index is None:
                for i, seg in enumerate(path_segments):
                    if getattr(seg, "lane", None) is not None and seg.lane.road_uid == target_road_uid:
                        reference_index = i
                        break
            if reference_index is None:
                return None

            current_seg = path_segments[reference_index]

            neighbor_index = reference_index + 1 if reference_index + 1 < len(path_segments) else reference_index - 1
            if neighbor_index < 0:
                return None
            neighbor_seg = path_segments[neighbor_index]

            def direction_by_adjacency() -> Direction | None:
                for direction in Direction:
                    if ts.get_adjacent_segment(current_seg.uid, direction) == neighbor_seg:
                        return direction
                for direction in Direction:
                    if ts.get_outgoing_adjacent_segment(current_seg.uid, direction) == neighbor_seg:
                        return direction
                return None

            path_direction = direction_by_adjacency()
            if path_direction is not None:
                return path_direction.opposite if neighbor_index < reference_index else path_direction

            current_pos = current_seg.get_position(ts)
            axis = 0 if road.orientation == RoadOrientation.HORIZONTAL else 1
            neighbor_pos = neighbor_seg.get_position(ts)

            if neighbor_pos[axis] == current_pos[axis] and len(path_segments) > 1:
                alt_index = reference_index - 1 if neighbor_index == reference_index + 1 else reference_index + 1
                if 0 <= alt_index < len(path_segments):
                    neighbor_seg = path_segments[alt_index]
                    neighbor_pos = neighbor_seg.get_position(ts)

            if neighbor_pos[axis] == current_pos[axis]:
                return None

            if neighbor_index < reference_index:
                current_pos, neighbor_pos = neighbor_pos, current_pos

            if road.orientation == RoadOrientation.HORIZONTAL:
                return Direction.RIGHT if neighbor_pos[0] > current_pos[0] else Direction.LEFT
            return Direction.DOWN if neighbor_pos[1] > current_pos[1] else Direction.UP

        def direction_from_car():
            car_direction: Direction
            if road.orientation == RoadOrientation.HORIZONTAL:
                car_direction = Direction.LEFT if (car.speed < 0) else Direction.RIGHT
            else:
                car_direction = Direction.DOWN if (car.speed < 0) else Direction.UP

            lane: Lane = self.segment.lane
            if should_ignore_lane_direction:
                lane = car.lane

            if not lane.is_forward():
                car_direction = car_direction.opposite
            return car_direction

        movement_direction = direction_from_path() or direction_from_car()

        if (road.orientation == RoadOrientation.HORIZONTAL and movement_direction in [Direction.UP, Direction.DOWN]
                or road.orientation == RoadOrientation.VERTICAL and movement_direction in [Direction.LEFT, Direction.RIGHT]):
            return self.interval

        if movement_direction == Direction.LEFT:
            right_end_segment = self.segment.get_size(ts)[0]
            return Interval(right_end_segment - self.interval.end, right_end_segment - self.interval.start)
        if movement_direction == Direction.DOWN:
            upper_end_segment = self.segment.get_size(ts)[1]
            return Interval(upper_end_segment - self.interval.end, upper_end_segment - self.interval.start)
        return self.interval

    def __str__(self):
        return f"{self.segment} {self.interval}"


@dataclass(frozen=True)
class ViewSegmentIntervall(SegmentInterval):
    """
    Represents a segment interval that is aligned to a virtual lane offset.
    """
    offset: float = 0.0
    path_segments: tuple[Segment, ...] | None = None

    def get_global_interval(self, ts: TrafficSnapshotReader, car: "Car",
                            should_ignore_lane_direction: bool = False) -> Interval:
        """
        Converts the virtual-lane interval into segment-relative coordinates by applying the offset,
        then returns the global interval.
        """
        shifted_interval = Interval(self.interval.start - self.offset, self.interval.end - self.offset)
        base_interval = SegmentInterval(self.segment, shifted_interval)

        if self.path_segments is None:
            return base_interval.get_global_interval(ts, car, should_ignore_lane_direction)

        class _CarProxy:
            def __init__(self, original_car: "Car", path_segments: tuple[Segment, ...]):
                self.speed = original_car.speed
                self.lane = original_car.lane
                self.environment = type("Env", (), {"path": path_segments})()

        proxy_car = _CarProxy(car, self.path_segments)
        return base_interval.get_global_interval(ts, proxy_car, should_ignore_lane_direction)
