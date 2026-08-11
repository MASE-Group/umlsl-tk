from dataclasses import dataclass
from enum import Enum

from umlsl_edit.model.entities.entity import Entity
from umlsl_edit.model.errors.road_errors import RoadValidationError
from umlsl_edit.model.helpers.uid_service import generate_uid
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.view.view_constants import DIMENSION


class RoadOrientation(Enum):
    """
    Enumeration representing the orientation of a road in the coordinate system.

    Attributes:
        HORIZONTAL: The road runs horizontally (left-right) in the coordinate system.
        VERTICAL: The road runs vertically (up-down) in the coordinate system.
    """

    HORIZONTAL = 0
    VERTICAL = 1

    def opposite(self) -> "RoadOrientation":
        """
        Returns the opposite orientation of the road.

        Returns:
            RoadOrientation: The opposite orientation (HORIZONTAL <-> VERTICAL).
        """
        if self == RoadOrientation.HORIZONTAL:
            return RoadOrientation.VERTICAL
        return RoadOrientation.HORIZONTAL


@dataclass
class RoadParams:
    """
    Type-safe parameter dictionary for Road creation.

    Supports all Road attributes with optional parameters marked appropriately.
    Use this with **kwargs to avoid repetitive parameter forwarding.

    Attributes:
        name: Unique human-readable identifier for the road.
        orientation: The orientation of the road (horizontal or vertical).
        position: The position of the road in the coordinate system.
        number_of_forward_lanes: Number of lanes in the forward direction
        number_of_backward_lanes: Number of lanes in the backward direction
    """

    name: str
    orientation: RoadOrientation
    position: float
    number_of_forward_lanes: int
    number_of_backward_lanes: int


@dataclass
class Road(Entity):
    """
    Represents a road in the traffic simulation system.

    A road is an infinite linear line with a specific orientation (horizontal or vertical)
    and contains one or more lanes in either forward or backward direction.
    Roads only define the number of forward and backward lanes.

    Attributes:
        name: Unique human-readable identifier for the road.
              Must be a non-empty string.
        orientation: The orientation of the road (HORIZONTAL or VERTICAL).
        position: The position of the road in the coordinate system along the
                  axis perpendicular to its orientation. For horizontal roads,
                  this is the Y-coordinate; for vertical roads, the X-coordinate.
        forward_lanes: Number of lanes in the forward direction
        backward_lanes: Number of lanes in the backward direction

    Raises:
        RoadValidationError: If name is empty, orientation is invalid,
                             or position is not a valid number.
    """

    name: str
    orientation: RoadOrientation
    position: float
    number_of_forward_lanes: int
    number_of_backward_lanes: int
    forward_lanes: list[Lane]
    backward_lanes: list[Lane]

    _should_validate: bool = False

    @classmethod
    def from_params(cls, params: RoadParams) -> "Road":
        """
        Creates a Road instance from a RoadParams object.

        Args:
            params: An instance of RoadParams containing the road attributes.
        Returns:
            A new Road instance with the provided parameters.
        """
        road_uid = generate_uid()
        forward_lanes = []
        backward_lanes = []
        for i in range(params.number_of_forward_lanes):
            forward_lanes.append(Lane(lane_index=i, road_uid=road_uid))
        for i in range(params.number_of_backward_lanes):
            backward_lanes.append(Lane(lane_index=-(i + 1), road_uid=road_uid))
        return cls(
            name=params.name,
            uid=road_uid,
            orientation=params.orientation,
            position=params.position,
            number_of_forward_lanes=params.number_of_forward_lanes,
            number_of_backward_lanes=params.number_of_backward_lanes,
            forward_lanes=forward_lanes,
            backward_lanes=backward_lanes,
        )

    @staticmethod
    def validate_params(params: RoadParams) -> None:
        if not isinstance(params.name, str):
            raise RoadValidationError(content="Name must be a string.")

        if params.name.strip() == "":
            raise RoadValidationError(content="Name cannot be empty.")

        if not isinstance(params.orientation, RoadOrientation):
            raise RoadValidationError(
                content="Orientation must be a RoadOrientation enum member."
            )

        if not isinstance(params.position, (int, float)):
            raise RoadValidationError(content="Position must be a number.")

        if (
            not isinstance(params.number_of_forward_lanes, int)
            or params.number_of_forward_lanes < 0
        ):
            raise RoadValidationError(
                content="Forward lanes must be a non-negative integer."
            )

        if (
            not isinstance(params.number_of_backward_lanes, int)
            or params.number_of_backward_lanes < 0
        ):
            raise RoadValidationError(
                content="Backward lanes must be a non-negative integer."
            )

        if params.number_of_forward_lanes == 0 and params.number_of_backward_lanes == 0:
            raise RoadValidationError(content="Road must have at least one lane.")

    def update_from_params(self, params: RoadParams) -> None:
        """
        Updates the Road instance's attributes based on a RoadParams object.

        Args:
            params: An instance of RoadParams containing the new road attributes.

        Raises:
            RoadValidationError: If any validation check fails.
        """
        self.validate_params(params)

        old_state = {
            "name": self.name,
            "orientation": self.orientation,
            "position": self.position,
            "number_of_forward_lanes": self.number_of_forward_lanes,
            "number_of_backward_lanes": self.number_of_backward_lanes,
            "forward_lanes": list(self.forward_lanes),
            "backward_lanes": list(self.backward_lanes),
            "_should_validate": self._should_validate,
        }

        try:
            self._should_validate = False
            self.name = params.name
            self.orientation = params.orientation
            self.position = params.position

            # THATS WRONG
            # Update forward lanes
            if params.number_of_forward_lanes > len(self.forward_lanes):
                for i in range(len(self.forward_lanes), params.number_of_forward_lanes):
                    self.forward_lanes.append(Lane(lane_index=i, road_uid=self.uid))
            elif params.number_of_forward_lanes < len(self.forward_lanes):
                self.forward_lanes = self.forward_lanes[
                    : params.number_of_forward_lanes
                ]

            # Update backward lanes
            if params.number_of_backward_lanes > len(self.backward_lanes):
                for i in range(
                    len(self.backward_lanes), params.number_of_backward_lanes
                ):
                    self.backward_lanes.append(
                        Lane(lane_index=-(i + 1), road_uid=self.uid)
                    )
            elif params.number_of_backward_lanes < len(self.backward_lanes):
                self.backward_lanes = self.backward_lanes[
                    : params.number_of_backward_lanes
                ]

            self.number_of_forward_lanes = params.number_of_forward_lanes
            self.number_of_backward_lanes = params.number_of_backward_lanes

            self.__post_init__()
        except Exception:
            self._should_validate = False
            self.name = old_state["name"]
            self.orientation = old_state["orientation"]
            self.position = old_state["position"]
            self.number_of_forward_lanes = old_state["number_of_forward_lanes"]
            self.number_of_backward_lanes = old_state["number_of_backward_lanes"]
            self.forward_lanes = list(old_state["forward_lanes"])
            self.backward_lanes = list(old_state["backward_lanes"])
            self._should_validate = old_state["_should_validate"]
            self.__post_init__()
            raise

    def __post_init__(self) -> None:
        """
        Validates the Road instance after initialization.

        Raises:
            RoadValidationError: If any validation check fails.
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

    def get_bounds(self) -> tuple[float, float]:
        """Calculate the bounds of the road based on its position and number of lanes on the relevant axis according
        to its orientation. The first value is the lower bound, the second value the upper bound."""
        lane_width = DIMENSION.LANE_WIDTH

        if self.orientation == RoadOrientation.HORIZONTAL:
            lower_bound = self.position - lane_width * len(self.forward_lanes)
            upper_bound = self.position + lane_width * len(self.backward_lanes)
        else:
            lower_bound = self.position - lane_width * len(self.backward_lanes)
            upper_bound = self.position + lane_width * len(self.forward_lanes)

        return lower_bound, upper_bound

    def validate(self) -> None:
        if not isinstance(self.name, str):
            raise RoadValidationError(content="Name must be a string.")

        if self.name.strip() == "":
            raise RoadValidationError(content="Name cannot be empty.")

        if not isinstance(self.orientation, RoadOrientation):
            raise RoadValidationError(
                content="Orientation must be a RoadOrientation enum member."
            )

        if not isinstance(self.position, (int, float)):
            raise RoadValidationError(content="Position must be a number.")

        if (
            not isinstance(self.number_of_forward_lanes, int)
            or self.number_of_forward_lanes < 0
        ):
            raise RoadValidationError(
                content="Forward lanes must be a non-negative integer."
            )

        if (
            not isinstance(self.number_of_backward_lanes, int)
            or self.number_of_backward_lanes < 0
        ):
            raise RoadValidationError(
                content="Backward lanes must be a non-negative integer."
            )

        if self.number_of_forward_lanes == 0 and self.number_of_backward_lanes == 0:
            raise RoadValidationError(content="Road must have at least one lane.")
