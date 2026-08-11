from dataclasses import dataclass, field

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.helpers.uid_service import generate_uid
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment


@dataclass(frozen=True, kw_only=True)
class LaneSegment(Segment):
    """The lane segment describes a segment of a single lane between two perpendicular roads."""
    uid: str = field(default_factory=generate_uid)
    lane: Lane
    is_lane_segment: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.lane, Lane):
            raise ValueError("lane must be a Lane")

    def get_position(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return position of the top left corner of the lane segment.
        It gets calculated from the position of the lane and adjacent crossings."""
        from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import CrossingSegment

        road = traffic_snapshot_reader.get_road_by_uid(self.lane.road_uid)
        lane_pos = self.lane.get_one_dimensional_position(traffic_snapshot_reader)
        lane_width = traffic_snapshot_reader.get_lane_width()

        if road.orientation == RoadOrientation.HORIZONTAL:
            # Horizontal lane: Y is fixed from lane position, X from left neighbor
            y = lane_pos
            left_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.LEFT)
            if left_neighbor is None:
                x = -traffic_snapshot_reader.get_scene_size()
            elif isinstance(left_neighbor, CrossingSegment):
                # Start after the crossing ends (crossing's right edge)
                x = left_neighbor.get_position(traffic_snapshot_reader)[0] + lane_width
            else:
                x = -traffic_snapshot_reader.get_scene_size()
        else:
            # Vertical lane: X is fixed from lane position, Y from top neighbor (higher y)
            x = lane_pos
            top_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.UP)
            if top_neighbor is None:
                y = traffic_snapshot_reader.get_scene_size()
            elif isinstance(top_neighbor, CrossingSegment):
                # Start after the crossing ends (crossing's bottom edge, higher y is up)
                y = top_neighbor.get_position(traffic_snapshot_reader)[1] - lane_width
            else:
                y = traffic_snapshot_reader.get_scene_size()

        return x, y

    def get_size(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return size (width, height) of the lane segment.
        It gets calculated from the road width and lane width."""
        from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import CrossingSegment

        road = traffic_snapshot_reader.get_road_by_uid(self.lane.road_uid)
        lane_width = traffic_snapshot_reader.get_lane_width()

        if road.orientation == RoadOrientation.HORIZONTAL:
            # Horizontal lane: height is lane_width, width varies based on crossings
            height = lane_width
            left_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.LEFT)
            right_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.RIGHT)

            scene_size = traffic_snapshot_reader.get_scene_size()
            if left_neighbor is None and isinstance(right_neighbor, CrossingSegment):
                right_x = right_neighbor.get_position(traffic_snapshot_reader)[0]
                width = right_x + scene_size
            elif right_neighbor is None and isinstance(left_neighbor, CrossingSegment):
                left_x = left_neighbor.get_position(traffic_snapshot_reader)[0]
                width = scene_size - (left_x + lane_width)
            elif isinstance(left_neighbor, CrossingSegment) and isinstance(right_neighbor, CrossingSegment):
                # Width = right_crossing.x - (left_crossing.x + lane_width)
                right_x = right_neighbor.get_position(traffic_snapshot_reader)[0]
                left_x = left_neighbor.get_position(traffic_snapshot_reader)[0]
                width = right_x - (left_x + lane_width)
            else:
                width = scene_size * 2  # No crossings, lane extends to the edge of the scene
        else:
            # Vertical lane: width is lane_width, height varies based on crossings
            width = lane_width
            top_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.UP)
            bottom_neighbor = traffic_snapshot_reader.get_adjacent_segment(self.uid, Direction.DOWN)

            scene_size = traffic_snapshot_reader.get_scene_size()
            if top_neighbor is None and isinstance(bottom_neighbor, CrossingSegment):
                bottom_y = bottom_neighbor.get_position(traffic_snapshot_reader)[1]
                height = scene_size - bottom_y
            elif bottom_neighbor is None and isinstance(top_neighbor, CrossingSegment):
                top_y = top_neighbor.get_position(traffic_snapshot_reader)[1]
                height = scene_size + top_y - lane_width
            elif isinstance(top_neighbor, CrossingSegment) and isinstance(bottom_neighbor, CrossingSegment):
                # Height = (top_crossing.y - lane_width) - bottom_crossing.y
                bottom_y = bottom_neighbor.get_position(traffic_snapshot_reader)[1]
                top_y = top_neighbor.get_position(traffic_snapshot_reader)[1]
                height = (top_y - lane_width) - bottom_y
            else:
                height = scene_size * 2  # No crossings, lane extends to the edge of the scene

        return width, height

    """"
    Returns the size in the direction of the lane.
    For example, for a horizontal lane, it returns the width, for a vertical lane it returns the height.
    """

    def get_size_in_direction(self, traffic_snapshot: TrafficSnapshotReader) -> float:
        road = self.lane.road_uid
        size = self.get_size(traffic_snapshot)
        match traffic_snapshot.get_road_by_uid(road).orientation:
            case RoadOrientation.HORIZONTAL:
                return size[0]
            case RoadOrientation.VERTICAL:
                return size[1]
