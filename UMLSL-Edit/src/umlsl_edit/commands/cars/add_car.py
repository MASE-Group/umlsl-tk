from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.model.entities.car import Car, CarParams


class AddCarCommand(Command[None]):
    """Creates a car object based on the provided parameters and adds it to the traffic snapshot."""

    def __init__(
            self,
            traffic_snapshot_reader: TrafficSnapshotReader,
            traffic_snapshot_writer: TrafficSnapshotWriter,
            settings_model: SettingsModel,
            car_params: CarParams
    ):
        """
        Initialize the AddCarCommand with car parameters.

        Args:
            traffic_snapshot_reader: Interface to read from the traffic snapshot.
            traffic_snapshot_writer: Interface to write to the traffic snapshot.
            car_params: Car creation parameters (name, assigned_road, lane_index, etc.).
        """
        self._traffic_snapshot_writer = traffic_snapshot_writer
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self._settings_model = settings_model
        self.car_params = car_params

    def execute(self) -> None:
        """
        Creates a Car instance using the provided parameters, validates it through
        Car.__post_init__, and adds it to the traffic snapshot.

        Raises:
            CarValidationError: If car parameter validation fails.
            CarTrafficSnapshotContextValidationError: If car is invalid in traffic snapshot context.
        """
        self._traffic_snapshot_reader.validate_car_params(self.car_params, True)
        car = Car.from_params(self.car_params, self._traffic_snapshot_reader, self._settings_model)
        self._traffic_snapshot_writer.add_car(car)