from umlsl_edit.model.errors.errors import BaseError, BaseWarning


class CarValidationError(BaseError):
    """
    Error raised when a Car entity fails the basic validation checks, whether all values are of the correct type and
    within acceptable ranges. No validation within the traffic_snapshot is performed here (See CarTrafficSnapshotContextValidationError).
    """
    def __init__(self, *, content: str) -> None:
        super().__init__(content=content, title="Car Validation Error")
    pass

class CarTrafficSnapshotContextValidationError(BaseError):
    """
    Error raised when a Car entity is invalid within the context of a specific traffic_snapshot, such as having a non-unique name.
    """

    def __init__(self, *, content: str) -> None:
        super().__init__(content=content, title="Car Validation Error in Traffic Snapshot Context")

    pass

class CarWarning(BaseWarning):
    """
    Warning raised for non-critical issues related to Car entities, to inform the user of potential problems without halting execution.
    """

    def __init__(self, *, content: str) -> None:
        super().__init__(content=content)

    pass
