from typing import TYPE_CHECKING

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import Car
    from umlsl_edit.model.entities.road import Road


class DataController:
    """Controller for providing data from the model to the view layer. It doesn't update anything automatic.
    It only serves data when requested."""

    def __init__(self, traffic_snapshot_reader: TrafficSnapshotReader):
        """
        Initialize the data controller.

        Args:
            traffic_snapshot_reader: The model that holds traffic simulation data.
        """
        self._traffic_snapshot_reader = traffic_snapshot_reader

    def replace_snapshot_reader(self, traffic_snapshot_reader: TrafficSnapshotReader) -> None:
        """
        Replace the underlying traffic snapshot reader (used during bulk reloads).
        """
        self._traffic_snapshot_reader = traffic_snapshot_reader

    def get_all_cars(self) -> dict[str, "Car"]:
        return self._traffic_snapshot_reader.get_cars()

    def get_all_roads(self) -> dict[str, "Road"]:
        return self._traffic_snapshot_reader.get_roads()

    def get_road_by_uid(self, uid: str) -> "Road":
        """Returns the road with the given uid."""
        return self._traffic_snapshot_reader.get_road_by_uid(uid)

    def get_valid_turn_intent_lanes(self, car_position: float, car_speed: float, car_lane: Lane, car_length: float,
                                    turn_direction: TurnDirection) -> list[Lane]:
        return self._traffic_snapshot_reader.get_valid_turn_intent_lanes(car_position, car_speed, car_lane, car_length,
                                                                         turn_direction)
