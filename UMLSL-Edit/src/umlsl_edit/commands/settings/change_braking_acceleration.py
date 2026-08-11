from umlsl_edit.commands.command import Command, ReturnValue
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.errors.settings_errors import SettingsValidationError


class ChangeBrakingAccelerationCommand(Command[None]):
    """
    Changes the braking acceleration of the cars based on the provided parameters.
    """

    def __init__(
            self,
            settings: SettingsModel,
            value: float
    ):
        """
        Initialize the ChangeBrakingAccelerationCommand with settings parameters.

        Args:
            settings: Settings object.
            value: Braking acceleration value.
        """
        self.value = value
        self._settings = settings

    def execute(self) -> ReturnValue:
        """
        Changes the braking acceleration.
        Raises:
            CommandValidationError: If command validation fails.
        """
        if self.value <= 0:
            raise SettingsValidationError("Braking acceleration must be a positive value.")
        self._settings.set_braking_acceleration(self.value)
