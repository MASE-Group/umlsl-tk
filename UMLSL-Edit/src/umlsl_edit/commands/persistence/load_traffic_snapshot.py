import json
from typing import TYPE_CHECKING

from umlsl_edit.commands.command import Command, CommandValidationError
from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)
from umlsl_edit.services.external_persistence_service import (
    ExternalPersistenceService,
)
from umlsl_edit.services.persistence_service import PersistenceService

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController


class LoadTrafficSnapshot(Command[None]):
    """Loads a traffic_snapshot from a specified file path and updates the application controller's traffic snapshot,
    which in turn basically reloads the program with the new traffic_snapshot."""

    def __init__(self, file_path: str, application_controller: "ApplicationController"):
        self._file_path = file_path
        self._application_controller = application_controller
        self.loaded_external = False
        """True when the opened file was in the UMLSL-Sim interchange format."""

    def execute(self) -> None:
        """Loads a traffic_snapshot from the specified file path and
         update the traffic snapshot in the application_controller.

        Files written by UMLSL-Sim (or by 'Export to UMLSL-Sim') are detected
        and read with the interchange deserializer, so that opening either
        format works.

        Raises:
            CommandValidationError: If command validation fails.
        """
        if not self._file_path:
            raise CommandValidationError("File path is required to load a snapshot.")

        try:
            with open(self._file_path, "r", encoding="utf-8") as file:
                raw_data = file.read()
        except OSError as exc:
            raise CommandValidationError(f"Failed to open snapshot: {exc}") from exc

        try:
            payload = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            raise CommandValidationError(f"Invalid JSON format: {exc}") from exc

        new_snapshot = TrafficSnapshotModel(self._application_controller.get_settings_model())
        new_queries = UMLSLQueriesModel(new_snapshot)

        self.loaded_external = ExternalPersistenceService.is_external_payload(payload)

        try:
            if self.loaded_external:
                ExternalPersistenceService.deserialize(
                    payload,
                    new_snapshot,
                    new_snapshot,
                    self._application_controller.get_settings_model(),
                )
            else:
                PersistenceService.deserialize(
                    payload,
                    new_snapshot,
                    new_snapshot,
                    self._application_controller.get_settings_model(),
                    new_queries,
                )
        except ValueError as exc:
            raise CommandValidationError(f"Failed to deserialize snapshot: {exc}") from exc

        self._application_controller.replace_snapshot(new_snapshot, new_queries)
