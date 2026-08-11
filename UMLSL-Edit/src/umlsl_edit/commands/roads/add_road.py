from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.model.entities.road import Road, RoadParams


class AddRoadCommand(Command[None]):
    """Creates a road object based on the provided parameters and adds it to the traffic snapshot."""

    def __init__(
            self,
            traffic_snapshot_reader: TrafficSnapshotReader,
            traffic_snapshot_writer: TrafficSnapshotWriter,
            road_params: RoadParams
    ):
        """
        Initialize the AddRoadCommand with road parameters.

        Args:
            traffic_snapshot_reader: Interface to read from the traffic snapshot.
            traffic_snapshot_writer: Interface to write to the traffic snapshot.
            road_params: Road creation parameters.
        """
        self._traffic_snapshot_writer = traffic_snapshot_writer
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self.road_params = road_params

    def execute(self) -> None:
        """
        Creates a Road instance using the provided parameters, validates it through
        Road.__post_init__, and adds it to the traffic snapshot.

        Raises:
            RoadValidationError: If road parameter validation fails.
            RoadTrafficSnapshotContextValidationError: If road is invalid in traffic snapshot context.
        """
        self._traffic_snapshot_reader.validate_road_params(self.road_params, True)
        road = Road.from_params(self.road_params)
        self._traffic_snapshot_writer.add_road(road)
