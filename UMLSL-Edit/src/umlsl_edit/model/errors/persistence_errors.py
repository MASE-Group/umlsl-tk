from umlsl_edit.model.errors.errors import BaseError


class TrafficSnapshotLoadingError(BaseError):
    """
    Error raised when there is an issue loading a traffic_snapshot from persistent storage. Probably due to file corruption
    or malformed data.
    """

    def __init__(self, *, content: str) -> None:
        super().__init__(content=content, title="Traffic Snapshot Loading Error")

    pass