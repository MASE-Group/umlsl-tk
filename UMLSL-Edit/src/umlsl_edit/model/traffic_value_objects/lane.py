from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
        TrafficSnapshotReader,
    )


class LaneDirection:
    FORWARD = 1
    BACKWARD = -1


@dataclass(frozen=True, kw_only=True)
class Lane:
    """Represents a lane on a road, this is an immutable data structure and should act like a tuple.
    It's not a full entity as it doesn't have an identity beyond its road, index and direction."""
    lane_index: int
    """The index of the lane, the inner most forward lane has index 0 and the inner most backward lane has index -1"""
    road_uid: str
    """The uid of the road this lane belongs to"""

    def __post_init__(self) -> None:
        """Validates the Lane instance after initialization.

        Performs the following validation checks:
        - lane_index must be an integer
        - road_uid must be a string
        """
        if not isinstance(self.road_uid, str):
            raise ValueError("road_uid must be a string")

        if not isinstance(self.lane_index, int):
            raise ValueError("lane_index must be a integer")

    def get_one_dimensional_position(self, traffic_snapshot_reader: 'TrafficSnapshotReader') -> float:
        road = traffic_snapshot_reader.get_road_by_uid(self.road_uid)
        lane_width = traffic_snapshot_reader.get_lane_width()
        if getattr(road.orientation, "name", None) == "HORIZONTAL":
            # Horizontal lanes: forward indices are lower y than backward indices.
            if self.lane_index >= 0:
                return road.position - self.lane_index * lane_width
            return road.position + (abs(self.lane_index)) * lane_width
        return road.position + self.lane_index * lane_width

    def get_name(self, traffic_snapshot_reader) -> str:
        road = traffic_snapshot_reader.get_road_by_uid(self.road_uid)
        if road.orientation.value == 0:
            return f"r{self.lane_index + 1}" if self.lane_index >= 0 else f"l{-self.lane_index}"
        else:
            return f"u{self.lane_index + 1}" if self.lane_index >= 0 else f"d{-self.lane_index}"

    def get_direction(self) -> int:
        return LaneDirection.FORWARD if self.lane_index >= 0 else LaneDirection.BACKWARD

    def is_forward(self) -> bool:
        return self.lane_index >= 0
