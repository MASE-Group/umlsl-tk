from dataclasses import dataclass

from umlsl_edit.model.helpers.event_types import SettingsEventType
from umlsl_edit.model.helpers.observables import Observable


@dataclass
class SettingsModel(Observable):
    """
    Holds simulation settings for braking deceleration and max speed.
    """

    braking_acceleration: float
    max_speed: float

    def __post_init__(self):
        """Initialize Observable after dataclass initialization."""
        Observable.__init__(self)

    def set_braking_acceleration(self, braking_deceleration: float):
        """
        Update braking deceleration and notify observers.
        """
        self.braking_acceleration = braking_deceleration
        self.notify(SettingsEventType.CHANGE_BRAKING_DECELERATION, braking_deceleration)

    def set_max_speed(self, max_speed: float):
        """
        Update the maximum speed and notify observers.
        """
        self.max_speed = max_speed
        self.notify(SettingsEventType.CHANGE_MAX_SPEED, max_speed)

    def braking_distance(self) -> float:
        return self.max_speed * self.max_speed / (2.0 * self.braking_acceleration)
