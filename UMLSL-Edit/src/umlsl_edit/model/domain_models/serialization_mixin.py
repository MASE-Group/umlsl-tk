import json
from typing import TYPE_CHECKING, Any

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.domain_models.traffic_snapshot_writer import TrafficSnapshotWriter
from umlsl_edit.model.entities.car import Car, CarParams
from umlsl_edit.model.entities.road import Road, RoadOrientation, RoadParams
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection, TurnIntent

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel

class SerializationMixin:
    def to_dict(self: "TrafficSnapshotModel") -> dict[str, Any]:
        """
        Serializes the TrafficSnapshot instance to a dictionary suitable for JSON encoding.
        """
        roads_data: list[dict[str, Any]] = []
        for road in self.get_roads().values():
            roads_data.append(
                {
                    "uid": road.uid,
                    "name": road.name,
                    "orientation": road.orientation.name,
                    "position": road.position,
                    "number_of_forward_lanes": road.number_of_forward_lanes,
                    "number_of_backward_lanes": road.number_of_backward_lanes,
                }
            )

        cars_data: list[dict[str, Any]] = []
        for car in self.get_car_list():
            car_payload: dict[str, Any] = {
                "uid": car.uid,
                "name": car.name,
                "road_uid": car.lane.road_uid,
                "lane_index": car.lane.lane_index,
                "position_on_lane": car.position_on_lane,
                "transition": car.transition,
                "speed": car.speed,
                "length": car.length,
                "color": car.color,
                "acceleration": car.acceleration,
            }

            if car.next_turn is not None:
                car_payload["next_turn"] = {
                    "direction": car.next_turn.direction.name,
                    "target_lane": {
                        "road_uid": car.next_turn.target_lane.road_uid,
                        "lane_index": car.next_turn.target_lane.lane_index,
                    },
                }
            else:
                car_payload["next_turn"] = None

            cars_data.append(car_payload)

        return {"roads": roads_data, "cars": cars_data}

    def to_json(self: "TrafficSnapshotModel") -> str:
        """
        Serializes the TrafficSnapshot instance to a JSON string.
        """
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(
            data: dict[str, Any],
            writer: TrafficSnapshotWriter,
            reader: TrafficSnapshotReader,
            settings_model: SettingsModel,
    ) -> "TrafficSnapshotModel":
        """
        Creates a TrafficSnapshot instance from a dictionary.

        Args:
            data: A dictionary containing 'roads' and 'cars' keys.
            writer: A TrafficSnapshotWriter instance that will receive new entities.
            reader: A TrafficSnapshotReader instance used for validation and lookups.
            settings_model: Settings used when constructing cars and validating context.

        Returns:
            The populated TrafficSnapshotModel instance.

        Raises:
            ValueError: If the payload is malformed or the writer is not a TrafficSnapshotModel.
        """
        # Note: We still do this dynamic import if necessary, but we can rely on TYPE_CHECKING
        from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel

        if not isinstance(data, dict):
            raise ValueError("Traffic snapshot data must be a dictionary.")

        roads_data = data.get("roads", [])
        cars_data = data.get("cars", [])

        if not isinstance(roads_data, list):
            raise ValueError("Traffic snapshot 'roads' must be a list.")
        if not isinstance(cars_data, list):
            raise ValueError("Traffic snapshot 'cars' must be a list.")

        for road_data in roads_data:
            if not isinstance(road_data, dict):
                raise ValueError("Each road must be a dictionary.")

            orientation_raw = road_data.get("orientation")
            if isinstance(orientation_raw, RoadOrientation):
                orientation = orientation_raw
            elif isinstance(orientation_raw, str):
                orientation = RoadOrientation[orientation_raw]
            else:
                orientation = RoadOrientation(orientation_raw)

            road_params = RoadParams(
                name=road_data["name"],
                orientation=orientation,
                position=road_data["position"],
                number_of_forward_lanes=road_data["number_of_forward_lanes"],
                number_of_backward_lanes=road_data["number_of_backward_lanes"],
            )
            reader.validate_road_params(road_params, True)

            road_uid = road_data.get("uid")
            if not road_uid:
                raise ValueError("Road uid is required.")
            forward_lanes = [
                Lane(lane_index=i, road_uid=road_uid)
                for i in range(road_params.number_of_forward_lanes)
            ]
            backward_lanes = [
                Lane(lane_index=-(i + 1), road_uid=road_uid)
                for i in range(road_params.number_of_backward_lanes)
            ]
            road = Road(
                uid=road_uid,
                name=road_params.name,
                orientation=road_params.orientation,
                position=road_params.position,
                number_of_forward_lanes=road_params.number_of_forward_lanes,
                number_of_backward_lanes=road_params.number_of_backward_lanes,
                forward_lanes=forward_lanes,
                backward_lanes=backward_lanes,
            )

            writer.add_road(road)

        for car_data in cars_data:
            if not isinstance(car_data, dict):
                raise ValueError("Each car must be a dictionary.")

            lane = Lane(
                road_uid=car_data["road_uid"],
                lane_index=car_data["lane_index"],
            )

            next_turn_data = car_data.get("next_turn")
            next_turn = None
            if isinstance(next_turn_data, dict):
                direction_raw = next_turn_data.get("direction")
                if isinstance(direction_raw, TurnDirection):
                    direction = direction_raw
                elif isinstance(direction_raw, str):
                    direction = TurnDirection[direction_raw]
                else:
                    direction = TurnDirection(direction_raw)

                target_lane_data = next_turn_data.get("target_lane", {})
                if (
                        isinstance(target_lane_data, dict)
                        and "road_uid" in target_lane_data
                        and "lane_index" in target_lane_data
                ):
                    target_lane = Lane(
                        road_uid=target_lane_data["road_uid"],
                        lane_index=target_lane_data["lane_index"],
                    )
                    next_turn = TurnIntent(direction=direction, target_lane=target_lane)

            car_params = CarParams(
                name=car_data["name"],
                lane=lane,
                color=car_data["color"],
                position_on_lane=car_data["position_on_lane"],
                transition=car_data.get("transition", 0.0),
                speed=car_data["speed"],
                length=car_data["length"],
                next_turn=next_turn,
                acceleration=car_data.get("acceleration", 0.0),
            )
            reader.validate_car_params(car_params, True)

            car = Car.from_params(car_params, reader, settings_model)
            car_uid = car_data.get("uid")
            if not car_uid:
                raise ValueError("Car uid is required.")
            car.uid = car_uid
            writer.add_car(car)

        if not isinstance(writer, TrafficSnapshotModel):
            raise ValueError(
                "TrafficSnapshotModel.from_dict expects a TrafficSnapshotModel writer."
            )
        return writer

    @classmethod
    def from_json(
            cls,
            json_string: str,
            settings_model: SettingsModel,
    ) -> "TrafficSnapshotModel":
        """
        Creates a TrafficSnapshot instance from a JSON string.

        Args:
            json_string: A JSON-formatted string containing traffic snapshot data.
            settings_model: A SettingsModel instance for validation during deserialization.
            queries_model: UMLSLQueriesModel instance required to construct the snapshot.

        Returns:
            A new TrafficSnapshotModel populated with the deserialized roads and cars.
        """
        import json
        data = json.loads(json_string)
        snapshot = cls(settings_model)
        cls.from_dict(data, snapshot, snapshot, settings_model)
        return snapshot
