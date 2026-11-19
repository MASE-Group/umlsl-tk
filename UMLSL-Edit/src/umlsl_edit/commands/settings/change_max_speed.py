from umlsl_edit.commands.command import Command, ReturnValue
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.errors.settings_errors import SettingsValidationError


class ChangeMaxSpeedCommand(Command[None]):
    """
    Changes the global maximum speed of the cars.
    """

    def __init__(
            self,
            settings: SettingsModel,
            value: float
    ):
        """
        Initialize the ChangeMaxSpeedCommand with settings parameters.

        Args:
            settings: Settings object.
            value: Maximum speed value.
        """
        self.value = value
        self._settings = settings

    def execute(self) -> ReturnValue:
        """
        Changes the maximum speed.
        Raises:
            SettingsValidationError: If the value is not positive.
        """
        if self.value <= 0:
            raise SettingsValidationError("Maximum speed must be a positive value.")
        self._settings.set_max_speed(self.value)
