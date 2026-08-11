import re
from dataclasses import dataclass
from typing import Optional

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.entities.entity import Entity
from umlsl_edit.model.environment.car_environment import CarEnvironment
from umlsl_edit.model.environment.environment_creation import (
    EnvironmentCreation,
)
from umlsl_edit.model.errors.car_errors import CarValidationError
from umlsl_edit.model.helpers.uid_service import generate_uid
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnIntent


@dataclass
class CarParams:
    """
    Type-safe parameter dictionary for Car creation.

    Supports all Car attributes with optional parameters marked appropriately.
    Use this with **kwargs to avoid repetitive parameter forwarding.

    Attributes:
        name: Unique human-readable identifier for the car.
        lane: Lane the car is currently in, defined by road, lane index, and direction.
        color: Hex color code for rendering.
        position_on_lane: Distance along the lane in units
        transition: Lane change progress from -1.0 to 1.0 exclusive
        speed: Current speed of the car in units per time step
        length: Physical length of the car in units
        next_turn: Optional intended turn behavior at the next intersection
    """

    name: str
    lane: Lane | None
    color: str
    position_on_lane: float
    transition: float
    speed: float
    length: float
    next_turn: TurnIntent | None
    acceleration: float

    def get_braking_dist(self, braking_acceleration: float):
        return (self.speed * self.speed) / (2.0 * braking_acceleration) + self.length


@dataclass()
class Car(Entity):
    """
    Represents a car/vehicle in the traffic simulation.

    A car is a movable entity that travels along lanes on roads. It has physical
    properties (length, color), kinematic properties (position, velocity), and
    navigational properties (assigned road, lane, transition state, next turn).

    Attributes:
        name: Unique human-readable identifier for the car. Must be a non-empty string.
        lane: Lane the car is currently in, defined by road, lane index, and direction.
        color: Hex color code for rendering the car.
        position_on_lane: Distance along the lane in units. Must be non-negative.
        transition: Lane change progress from -1.0 (fully left) to 1.0 (fully right).
                    Value of 0.0 means centered in current lane. Bounds are exclusive.
        speed: Current speed of the car in units per time step. Can be negative for reverse.
        length: Physical length of the car in units. Must be positive.
        next_turn: Optional intended turn behavior at the next intersection.

        reserved_lanes: List of LaneSegments reserved by the car for future movement.
        claimed_lanes: List of LaneSegments currently claimed by the car.
        reserved_crossings: List of CrossingSegments reserved by the car.
        claimed_crossings: List of CrossingSegments currently claimed by the car.
        path: Path is list of LaneSegments and CrossingSegments representing the planned route.
        acceleration: Current acceleration of the car in units per time step squared.

    Raises:
        CarValidationError: If any validation check fails during instantiation.
    """

    name: str

    lane: Lane

    color: str

    position_on_lane: float

    transition: float

    speed: float

    length: float

    next_turn: Optional[TurnIntent]

    environment: CarEnvironment
    acceleration: float

    _should_validate: bool = False

    @classmethod
    def from_params(
        cls,
        params: CarParams,
        traffic_snapshot: TrafficSnapshotReader,
        settings_model: SettingsModel,
    ) -> "Car":
        """
        Creates a Car instance from a CarParams dataclass.

        Args:
            params: CarParams instance containing all car attributes.

        Returns:
            A new Car instance with attributes from the params.
        """

        # if params.next_turn is None:
        #     car_env = CarEnvironment.empty()
        # else:
        #     car_env = CarEnvironment.create_environment(
        #         ts_reader,
        #         params.lane,
        #         params.position_on_lane,
        #         params.length,
        #         params.speed,
        #         params.next_turn,
        #     )

        car_env = EnvironmentCreation(traffic_snapshot, params, settings_model).build()
        return cls(
            uid=generate_uid(),
            name=params.name,
            lane=params.lane,
            color=params.color,
            position_on_lane=params.position_on_lane,
            transition=params.transition,
            speed=params.speed,
            length=params.length,
            next_turn=params.next_turn,
            environment=car_env,
            acceleration=params.acceleration,
        )

    def __post_init__(self) -> None:
        """
        Validates the Car attributes after initialization without checking them in the TrafficSnapshot context.

        Raises:
            CarValidationError: If any validation check fails.
        """
        self.validate()
        self._initialized = True
        self._should_validate = True

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if getattr(self, "_initialized", False) and getattr(
            self, "_should_validate", True
        ):
            self.validate()

    def validate(self) -> None:
        if not isinstance(self.name, str):
            raise CarValidationError(content="Name must be a non-empty string.")

        if self.name.strip() == "":
            raise CarValidationError(content="Name cannot be empty.")

        if not isinstance(self.lane, Lane):
            raise CarValidationError(content="Lane must be a Lane instance.")

        if not isinstance(self.color, str) or not re.match(
            r"^#(?:[0-9a-fA-F]{3}){1,2}$", self.color
        ):
            """
            No need for color checking. Color can be hex or a color name like red, blue, green, etc.
            If string doesnt match hex code or color name, it will result in black.
            If you want to enforce hex color codes only, uncomment the following line.
            """
            # raise CarValidationError(content="Color must be a valid hex color code.")
            pass

        # Transition bounds check (-1.0, 1.0) exclusive
        if not (-1.0 < self.transition < 1.0):
            raise CarValidationError(
                content="Transition must be in the range (-1.0, 1.0) exclusive."
            )

        if not isinstance(self.speed, (int, float)):
            raise CarValidationError(content="Velocity must be a number.")

        if self.length <= 0:
            raise CarValidationError(content="Length must be a positive number.")

        if self.next_turn is not None and not isinstance(self.next_turn, TurnIntent):
            raise CarValidationError(
                content="Next turn must be None or a TurnIntent instance."
            )

    @staticmethod
    def validate_params(params: CarParams) -> None:
        if not isinstance(params.name, str):
            raise CarValidationError(content="Name must be a non-empty string.")

        if params.name.strip() == "":
            raise CarValidationError(content="Name cannot be empty.")

        if not isinstance(params.lane, Lane):
            raise CarValidationError(content="Lane must be a Lane instance.")

        # Transition bounds check (-1.0, 1.0) exclusive
        if not (-1.0 < params.transition < 1.0):
            raise CarValidationError(
                content="Transition must be in the range (-1.0, 1.0) exclusive."
            )

        if not isinstance(params.speed, (int, float)):
            raise CarValidationError(content="Velocity must be a number.")

        if params.length <= 0:
            raise CarValidationError(content="Length must be a positive number.")

        if params.next_turn is not None and not isinstance(
            params.next_turn, TurnIntent
        ):
            raise CarValidationError(
                content="Next turn must be None or a TurnIntent instance."
            )

    def update_from_params(
        self,
        params: CarParams,
        traffic_snapshot: TrafficSnapshotReader,
        settings_model: SettingsModel,
    ) -> None:
        """
        Updates the Car instance's attributes based on a CarParams dataclass.

        Args:
            params: CarParams instance containing updated car attributes.
            traffic_snapshot: TrafficSnapshot instance containing updated traffic snapshot data.
            settings_model: SettingsModel instance containing updated settings.

        Raises:
            CarValidationError: If any validation check fails.
        """

        # if params.next_turn is None:
        #     car_env = CarEnvironment.empty()
        # else:
        #     car_env = CarEnvironment.create_environment(
        #         ts_reader,
        #         params.lane,
        #         params.position_on_lane,
        #         params.length,
        #         params.speed,
        #         params.next_turn,
        #     )

        self.validate_params(params)

        old_state = {
            "name": self.name,
            "lane": self.lane,
            "color": self.color,
            "position_on_lane": self.position_on_lane,
            "transition": self.transition,
            "speed": self.speed,
            "length": self.length,
            "next_turn": self.next_turn,
            "acceleration": self.acceleration,
            "_should_validate": self._should_validate,
        }

        try:
            self._should_validate = False
            self.name = params.name
            self.lane = params.lane
            self.color = params.color
            self.position_on_lane = params.position_on_lane
            self.transition = params.transition
            self.speed = params.speed
            self.length = params.length
            self.next_turn = params.next_turn
            self.acceleration = params.acceleration
            self.__post_init__()
            self.recalculate_environment(traffic_snapshot, settings_model)
        except Exception:
            self._should_validate = False
            self.name = old_state["name"]
            self.lane = old_state["lane"]
            self.color = old_state["color"]
            self.position_on_lane = old_state["position_on_lane"]
            self.transition = old_state["transition"]
            self.speed = old_state["speed"]
            self.length = old_state["length"]
            self.next_turn = old_state["next_turn"]
            self.acceleration = old_state["acceleration"]
            self._should_validate = old_state["_should_validate"]
            self.__post_init__()
            raise

    def recalculate_environment(
        self, traffic_snapshot: TrafficSnapshotReader, settings_model: SettingsModel
    ) -> None:
        self.environment = EnvironmentCreation(
            traffic_snapshot,
            CarParams(
                name=self.name,
                lane=self.lane,
                color=self.color,
                position_on_lane=self.position_on_lane,
                transition=self.transition,
                speed=self.speed,
                length=self.length,
                next_turn=self.next_turn,
                acceleration=self.acceleration,
            ),
            settings_model,
        ).build()

