from dataclasses import dataclass
from enum import Enum

from umlsl_edit.model.traffic_value_objects.lane import Lane


class TurnDirection(Enum):
    """
    Enumeration representing
    the direction of a turn at an intersection.

    Attributes:
        LEFT: The car intends to turn left at the next intersection.
        RIGHT: The car intends to turn right at the next intersection.
    """

    LEFT = 0
    RIGHT = 1
    STRAIGHT = 2


@dataclass(frozen=True)
class TurnIntent:
    """
    Encapsulates the intended turn behavior at the next intersection.

    This dataclass represents the car's intention to turn at an upcoming
    intersection, specifying both the direction of the turn and the target
    lane the car wants to enter after completing the turn.

    Attributes:
        direction: The direction of the intended turn (LEFT or RIGHT).
        target_lane: The lane the car intends to occupy after the turn.

    Raises:
        CarValidationError: If direction is not a TurnDirection or target_lane is not a Lane.
    """

    direction: TurnDirection

    target_lane: Lane

    def __post_init__(self) -> None:
        """
        Validates the TurnIntent instance after initialization.

        Performs the following validation checks:
        - direction must be a valid TurnDirection enum value
        - target_lane must be a valid Lane instance
        """
        if not isinstance(self.direction, TurnDirection):
            raise ValueError("direction must be a TurnDirection")
        if not isinstance(self.target_lane, Lane):
            raise ValueError("target_lane must be a Lane")
