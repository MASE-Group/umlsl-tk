from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.domain_models.traffic_snapshot_writer import TrafficSnapshotWriter
from umlsl_edit.model.errors.road_errors import RoadValidationError


class DeleteRoad(Command[None]):
    """Deletes a road from the traffic snapshot based on its unique identifier."""

    def __init__(
            self,
            traffic_snapshot_writer: TrafficSnapshotWriter,
            traffic_snapshot_reader: TrafficSnapshotReader,
            road_uid: str
    ):
        """
        Initialize the DeleteRoadCommand with the road's unique identifier.

        Args:
            traffic_snapshot_writer: Interface to write to the traffic snapshot.
            traffic_snapshot_reader: Interface to read from the traffic snapshot.
            road_uid: Unique identifier of the road to be deleted.
        """
        self._traffic_snapshot_writer = traffic_snapshot_writer
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self.road_uid = road_uid

    def execute(self) -> None:
        """
        Deletes the road with the specified unique identifier from the traffic snapshot.

        Raises:
            RoadValidationError: If command validation fails.
        """
        try:
            self._traffic_snapshot_reader.get_road_by_uid(self.road_uid)
        except ValueError:
            raise RoadValidationError(content=f"Road with UID {self.road_uid} does not exist and cannot be deleted.")
        self._traffic_snapshot_writer.remove_road(self.road_uid)
