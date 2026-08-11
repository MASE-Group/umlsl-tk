from umlsl_edit.commands.command import Command
from umlsl_edit.model.errors.car_errors import CarValidationError


class DeleteCar(Command[None]):
    """Deletes a car from the traffic snapshot based on its unique identifier."""

    def __init__(
            self,
            traffic_snapshot_writer,
            traffic_snapshot_reader,
            car_uid: str
    ):
        """
        Initialize the DeleteCarCommand with the car's unique identifier.

        Args:
            traffic_snapshot_writer: Interface to write to the traffic snapshot.
            traffic_snapshot_reader: Interface to read from the traffic snapshot.
            car_uid: Unique identifier of the car to be deleted.
        """
        self._traffic_snapshot_writer = traffic_snapshot_writer
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self.uid = car_uid

    def execute(self) -> None:
        """
        Deletes the car with the specified unique identifier from the traffic snapshot.

        Raises:
            CarValidationError: If command validation fails.
        """
        if self._traffic_snapshot_reader.is_car_existing(self.uid) is False:
            raise CarValidationError(content=f"Car with UID {self.uid} does not exist and cannot be deleted.")
        self._traffic_snapshot_writer.remove_car(self.uid)
