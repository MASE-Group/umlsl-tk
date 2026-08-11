from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.model.entities.road import RoadParams
from umlsl_edit.model.errors.road_errors import RoadValidationError


class EditRoadCommand(Command[None]):
    """Edits the properties of an existing road in the traffic snapshot."""

    def __init__(
            self,
            traffic_snapshot_reader: TrafficSnapshotReader,
            traffic_snapshot_writer: TrafficSnapshotWriter,
            road_params: RoadParams,
            uid: str
    ):
        """
        Initialize the EditRoadCommand with the road's unique identifier and updated parameters.

        Args:
            traffic_snapshot_reader: Interface to read from the traffic snapshot.
            traffic_snapshot_writer: Interface to write to the traffic snapshot.
            road_params: Parameters to change
            uid: Unique identifier of the road to be edited.
        """
        self._traffic_snapshot_writer = traffic_snapshot_writer
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self.road_params = road_params
        self.road_uid = uid

    def execute(self) -> None:
        """
        Edits the properties of the road with the specified unique identifier in the traffic snapshot.

        Raises:
            RoadValidationError: If road parameter validation fails.
            RoadTrafficSnapshotContextValidationError: If road is invalid in traffic snapshot context.
        """
        if not self._traffic_snapshot_reader.is_road_existing(self.road_uid):
            raise RoadValidationError(content=f"Road with UID {self.road_uid} does not exist and cannot be edited.")

        self._traffic_snapshot_reader.validate_road_params(self.road_params, False, self.road_uid)
        self._traffic_snapshot_writer.update_road(self.road_uid, self.road_params)
