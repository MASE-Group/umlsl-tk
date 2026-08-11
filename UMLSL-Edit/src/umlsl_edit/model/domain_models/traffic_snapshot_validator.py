from typing import TYPE_CHECKING

from umlsl_edit.model.entities.road import RoadOrientation, RoadParams
from umlsl_edit.model.environment.environment_creation import (
    EnvironmentCreation,
)
from umlsl_edit.model.errors.car_errors import (
    CarTrafficSnapshotContextValidationError,
)
from umlsl_edit.model.errors.road_errors import (
    RoadTrafficSnapshotContextValidationError,
)
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnIntent
from umlsl_edit.query.lexer import TokenType
from umlsl_edit.view.view_constants import DIMENSION

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import (
        TrafficSnapshotModel,
    )
    from umlsl_edit.model.domain_models.umlsl_queries_model import (
        UMLSLQueriesModel,
    )
    from umlsl_edit.model.entities.car import Car, CarParams


class TrafficSnapshotValidator:
    """
    Handles validation logic for the TrafficSnapshotModel.
    Separated to keep the model clean and focused on state management.
    """

    def __init__(self, model: "TrafficSnapshotModel"):
        self._model = model

    def validate_queries(self, queries_model: "UMLSLQueriesModel") -> None:
        """
        Validates all UMLSL queries in the context of the traffic snapshot.

        Args:
            queries_model: The UMLSLQueriesModel containing the queries to validate.
        """
        queries = queries_model.get_queries()
        invalid_query_ids: list[str] = []
        for query in queries.values():
            if not self._model.is_car_existing(query.assigned_car_uid):
                invalid_query_ids.append(query.uid)

        for query_id in invalid_query_ids:
            queries_model.remove_umlsl_query(query_id)

    def validate_car_params(
        self, car: "CarParams", new_instantiation: bool, car_uid: str | None = None
    ) -> None:
        """
        Validates a Car instance within the context of the TrafficSnapshot and throw errors if invalid.

        Args:
            car: The Car instance to validate.
            new_instantiation: Whether the car is being newly instantiated (True) or updated (False).
            car_uid: The car uid of the car to validate.

        Raises:
            CarTrafficSnapshotContextValidationError: If any validation check fails.
        """
        if not self._check_name_unique(car.name, car_uid):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car name '{car.name}' is not unique in the traffic snapshot."
            )
        if not self._check_lane_valid(car.lane):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car '{car.name}' has an invalid lane: {car.lane}."
            )
        if not EnvironmentCreation.validate_environment(
            self._model, car.position_on_lane, car.lane
        ):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car '{car.name}' cannot be placed inside a crossing."
            )
        if not self._check_transition_valid(car.transition, car.lane, car.speed < 0):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car '{car.name}' has an invalid transition: {car.transition} from lane {car.lane}."
            )
        if not self._check_no_tokens_contained(car.name):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car '{car.name}' cannot contain any of the umlsl language tokens."
            )
        if (
            car.get_braking_dist(self._model.settings_model.braking_acceleration)
            > self._model.settings_model.braking_distance()
        ):
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car '{car.name}' has a braking distance that exceeds the maximum allowed by the settings."
            )

    def validate_car_and_autocorrect(self, car: "Car") -> bool:
        """
        Validates a Car instance within the context of the TrafficSnapshot and autocorrects if possible.

        Returns:
            True if the car is still valid, False if the car is no longer able to be in the traffic snapshot and should
            get removed.

        Args:
            car: The Car instance to validate.
        """
        # if EnvironmentCreation.validate_environment(self._model, car.position_on_lane, car.lane):
        #     return False
        if not self._check_lane_valid(car.lane):
            return False
        if not self._check_transition_valid(car.transition, car.lane, car.speed < 0):
            car.transition = 0.0
        if car.next_turn is not None:
            if not self._check_turn_intent_valid(car.next_turn):
                car.next_turn = None
            else:
                valid_turn_lanes = self._model.get_valid_turn_intent_lanes(
                    car.position_on_lane,
                    car.speed,
                    car.lane,
                    car.length,
                    car.next_turn.direction,
                )
                if car.next_turn.target_lane not in valid_turn_lanes:
                    car.next_turn = None
        return True

    def validate_road_params(
        self, road_params: RoadParams, new_instantiation: bool, road_uid: str | None
    ) -> None:
        """
        Validates a Road instance within the context of the TrafficSnapshot.

        Args:
            road_params: The Road instance to validate.
            new_instantiation: Whether the road is being newly instantiated (True) or updated (False).
            road_uid: The UID of the road being updated, None if it's a new instantiation.

        Raises:
            RoadTrafficSnapshotContextValidationError: If any validation check fails.
        """
        if new_instantiation:
            if not self._check_name_unique(road_params.name):
                raise RoadTrafficSnapshotContextValidationError(
                    content=f"Road name '{road_params.name}' is not unique in the traffic snapshot."
                )
        else:
            if road_uid is None:
                raise ValueError("road_uid must be provided for road editing.")
            if not self._check_name_unique(road_params.name, road_uid):
                raise RoadTrafficSnapshotContextValidationError(
                    content=f"Road name '{road_params.name}' is not unique in the traffic snapshot."
                )
            if any(
                road.name == road_params.name and road.uid != road_uid
                for road in self._model.get_roads().values()
            ):
                raise RoadTrafficSnapshotContextValidationError(
                    content=f"Road name '{road_params.name}' is not unique in the traffic snapshot."
                )

        if not self._check_no_tokens_contained(road_params.name):
            raise RoadTrafficSnapshotContextValidationError(
                content=f"Road '{road_params.name}' cannot contain any of the umlsl language tokens."
            )

        roads = self._model.get_roads().values()
        if road_params.orientation == RoadOrientation.HORIZONTAL:
            bounds: tuple[float, float] = (
                road_params.position
                - road_params.number_of_forward_lanes * DIMENSION.LANE_WIDTH,
                road_params.position
                + road_params.number_of_backward_lanes * DIMENSION.LANE_WIDTH,
            )
        else:
            bounds: tuple[float, float] = (
                road_params.position
                - road_params.number_of_backward_lanes * DIMENSION.LANE_WIDTH,
                road_params.position
                + road_params.number_of_forward_lanes * DIMENSION.LANE_WIDTH,
            )
        for road in roads:
            if road_uid is not None and road_uid == road.uid:
                continue
            if road.orientation == road_params.orientation:
                road_bounds = road.get_bounds()
                if max(bounds[0], road_bounds[0]) < min(bounds[1], road_bounds[1]):
                    raise RoadTrafficSnapshotContextValidationError(
                        content="Roads cannot overlap each other. Please change position or number of forward or backward lanes."
                    )

    def _check_no_tokens_contained(self, text: str) -> bool:
        return not any(token.value in text for token in TokenType)

    def _check_name_unique(self, name: str, uid: str | None = None) -> bool:
        for car in self._model.cars.values():
            if car.name == name and car.uid != uid:
                return False
        for road in self._model.roads.values():
            if road.name == name and road.uid != uid:
                return False
        return True

    def _check_uid_unique(self, uid: str) -> bool:
        for car in self._model.cars.values():
            if car.uid == uid:
                return False
        for road in self._model.roads.values():
            if road.uid == uid:
                return False
        return True

    def _check_lane_valid(self, lane: Lane) -> bool:
        """Check if the lane exists in the traffic snapshot."""
        try:
            road = self._model.get_road_by_uid(lane.road_uid)
        except ValueError:
            return False
        return lane in (road.forward_lanes + road.backward_lanes)

    def _check_transition_valid(
        self, transition: float, lane: Lane, car_driving_backwards: bool
    ) -> bool:
        """Check if the transition value is valid for the given lane. It is not valid if the car changes out of the road,
        because right or left of the road is no lane. The transition value is aligned with the axes
        (1 means up/right, -1 means down/left)."""
        if transition == 0.0:
            return True
        try:
            road = self._model.get_road_by_uid(lane.road_uid)
        except ValueError:
            return False

        delta = 1 if transition > 0 else -1
        if getattr(road.orientation, "name", None) == "HORIZONTAL":
            delta = -delta
        new_lane_index = lane.lane_index + delta

        if new_lane_index >= 0:
            return new_lane_index <= len(road.forward_lanes) - 1
        return new_lane_index >= -len(road.backward_lanes)

    def _check_turn_intent_valid(self, turn_intent: TurnIntent) -> bool:
        target_lane = turn_intent.target_lane
        return self._check_lane_valid(target_lane)
