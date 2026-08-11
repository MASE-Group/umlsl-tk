from dataclasses import dataclass, field

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.helpers.uid_service import generate_uid
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment


@dataclass(frozen=True, kw_only=True)
class CrossingSegment(Segment):
    horizontal_lane: Lane
    vertical_lane: Lane
    uid:str=field(default_factory=generate_uid)
    is_lane_segment: bool = field(default=False, init=False)


    def __post_init__(self) -> None:
        if not isinstance(self.horizontal_lane, Lane):
            raise ValueError("lane_horizontal must be a Lane")
        if not isinstance(self.vertical_lane, Lane):
            raise ValueError("lane_vertical must be a Lane")
        pass

    def get_position(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return position of the top left corner of the crossing segment.
        It gets calculated from the position of the two lanes.

        horizontal_lane gives Y position (horizontal road's position is Y-coordinate)
        vertical_lane gives X position (vertical road's position is X-coordinate)
        """
        x = self.vertical_lane.get_one_dimensional_position(traffic_snapshot_reader)
        y = self.horizontal_lane.get_one_dimensional_position(traffic_snapshot_reader)
        return x, y

    def get_size(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return size (width, height) of the crossing segment.
        It gets calculated from the lane width."""
        lane_width = traffic_snapshot_reader.get_lane_width()
        return lane_width, lane_width

    def get_size_in_direction(self, traffic_snapshot_reader: TrafficSnapshotReader) -> float:
        # crossings segments are always square
        return traffic_snapshot_reader.get_lane_width()
