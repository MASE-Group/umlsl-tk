import json
import os

from umlsl_edit.commands.command import Command, CommandValidationError
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.services.external_persistence_service import (
    ExternalPersistenceService,
)


class ExportSnapshot(Command[None]):
    """Writes the current traffic snapshot to a file in the UMLSL-Sim interchange format.

    UMLSL queries are not part of the interchange format, so they are not
    exported; only roads and cars are carried over.
    """

    def __init__(self, file_path: str, traffic_snapshot_reader: TrafficSnapshotReader):
        """
        Initialize the ExportSnapshot command with the target file path.

        Args:
            file_path: The path where the traffic snapshot will be exported.
            traffic_snapshot_reader: The traffic snapshot reader for the current application.
        """
        self._file_path = file_path
        self._traffic_snapshot_reader = traffic_snapshot_reader

    def execute(self) -> None:
        """
        Exports the current traffic snapshot to the specified file path.

        Raises:
            CommandValidationError: If command validation fails.
        """
        if not self._file_path:
            raise CommandValidationError("File path is required to save a snapshot.")

        try:
            filename_without_ext = os.path.splitext(os.path.basename(self._file_path))[0]
            payload = ExternalPersistenceService.serialize(
                snapshot=self._traffic_snapshot_reader,
                filename=filename_without_ext
            )
        except ValueError as exc:
            raise CommandValidationError(f"Failed to serialize snapshot: {exc}") from exc

        try:
            with open(self._file_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
        except OSError as exc:
            raise CommandValidationError(f"Failed to save snapshot: {exc}") from exc
