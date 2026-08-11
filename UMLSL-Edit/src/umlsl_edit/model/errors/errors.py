class BaseError(Exception):
    """Base class for all custom errors in the UMLSL editor model."""
    def __init__(self, *, content: str, title: str) -> None:
        super().__init__(content)
        self.content = content
        self.title = title

class BaseWarning:
    """Base class for all custom warnings in the UMLSL editor model."""
    def __init__(self, *, content: str) -> None:
        self.content = content
    pass
