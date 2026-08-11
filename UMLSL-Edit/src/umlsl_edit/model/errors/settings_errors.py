from umlsl_edit.model.errors.errors import BaseError


class SettingsValidationError(BaseError):
    """Exception raised for errors in the settings validation."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(content=message, title="Settings Validation Error")
