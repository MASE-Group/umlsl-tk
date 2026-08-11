from umlsl_edit.model.errors.errors import BaseError, BaseWarning


class RoadValidationError(BaseError):
    """
    Error raised when a Road entity fails the basic validation checks, whether all values are of the correct type and
    within acceptable ranges. No validation within the traffic_snapshot is performed here (See CarTrafficSnapshotContextValidationError).
    """
    def __init__(self, *, content: str) -> None:
        super().__init__(content=content, title="Road Validation Error")
    pass

class RoadTrafficSnapshotContextValidationError(BaseError):
    """
    Error raised when a Road entity is invalid within the context of a specific traffic_snapshot, such as being assigned
    to a lane that does not exist in that snapshot for example.
    """

    def __init__(self, *, content: str) -> None:
        super().__init__(content=content, title="Road Validation Error in Traffic Snapshot Context")

    pass


class RoadWarning(BaseWarning):
    """
    Warning raised for non-critical issues related to Road entities, to inform the user of potential problems without halting execution.
    """

    def __init__(self, *, content: str) -> None:
        super().__init__(content=content)

    pass
