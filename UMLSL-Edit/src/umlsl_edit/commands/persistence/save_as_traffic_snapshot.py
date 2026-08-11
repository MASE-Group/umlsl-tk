import json

from umlsl_edit.commands.command import Command, CommandValidationError
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)
from umlsl_edit.services.persistence_service import PersistenceService


class SaveAsTrafficSnapshot(Command[None]):
    """Saves the current traffic snapshot to a specified file path."""

    def __init__(self, file_path: str, traffic_snapshot_reader: TrafficSnapshotReader, umlsl_queries: UMLSLQueriesModel):
        """
        Initialize the SaveAsTrafficSnapshot command with the target file path.

        Args:
            file_path: The path where the traffic snapshot will be saved.
            traffic_snapshot_reader: The traffic snapshot reader for the current application.
            umlsl_queries: The UMLSL queries interface for accessing UMLSL-related data.
        """
        self._file_path = file_path
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self._umlsl_queries = umlsl_queries

    def execute(self) -> None:
        """
        Saves the current traffic snapshot to the specified file path.

        Raises:
            CommandValidationError: If command validation fails.
        """
        if not self._file_path:
            raise CommandValidationError("File path is required to save a snapshot.")

        try:
            payload = PersistenceService.serialize(
                snapshot=self._traffic_snapshot_reader,
                queries=self._umlsl_queries,
            )
        except ValueError as exc:
            raise CommandValidationError(f"Failed to serialize snapshot: {exc}") from exc

        try:
            with open(self._file_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)
        except OSError as exc:
            raise CommandValidationError(f"Failed to save snapshot: {exc}") from exc
