from umlsl_edit.model.errors.errors import BaseError


class UMLSLQueryValidationError(BaseError):
    """
    Custom exception raised when UMLSLQuery validation fails.
    """

    def __init__(self, message: str):
        super().__init__(title="UMLSL Query Validation Error", content=message)
