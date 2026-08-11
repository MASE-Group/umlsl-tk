from abc import ABC, abstractmethod
from dataclasses import dataclass

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader


@dataclass(frozen=True)
class Segment(ABC):
    # todo: use enum
    is_lane_segment: bool
    uid: str

    @abstractmethod
    def get_position(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return position of the top left corner of the path.
        It gets calculated from the position of the first segment."""
        pass

    @abstractmethod
    def get_size(self, traffic_snapshot_reader: TrafficSnapshotReader) -> tuple[float, float]:
        """Return size (width, height) of the path."""
        pass

    @abstractmethod
    def get_size_in_direction(self, traffic_snapshot_reader: TrafficSnapshotReader) -> float:
        """Return size in the direction of the road."""
        pass
