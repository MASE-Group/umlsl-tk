import json
import os

from umlsl_edit.commands.command import Command, CommandValidationError
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.services.simulator_scenario import (
    SimulationIssue,
    build_simulator_scenario,
)


class SimulatorIncompatibleError(CommandValidationError):
    """Raised when UMLSL-Sim could not load or run the exported scenario."""

    def __init__(self, errors: list[SimulationIssue]):
        self.errors = errors
        super().__init__("\n".join(f"• {e.message}" for e in errors))


class ExportSnapshot(Command[None]):
    """Writes the current traffic snapshot to a file in the UMLSL-Sim interchange format.

    UMLSL queries are not part of the interchange format, so they are not
    exported; only roads and cars are carried over. A snapshot that UMLSL-Sim
    could not run is not written at all.
    """

    def __init__(
            self,
            file_path: str,
            traffic_snapshot_reader: TrafficSnapshotReader,
            max_speed: float | None = None,
    ):
        """
        Initialize the ExportSnapshot command with the target file path.

        Args:
            file_path: The path where the traffic snapshot will be exported.
                Its file stem becomes the scenario key.
            traffic_snapshot_reader: The traffic snapshot reader for the current application.
            max_speed: The editor's global maximum speed, written as every car's
                ``max_speed``. ``None`` keeps each car's current speed.
        """
        self._file_path = file_path
        self._traffic_snapshot_reader = traffic_snapshot_reader
        self._max_speed = max_speed

    def execute(self) -> None:
        """
        Exports the current traffic snapshot to the specified file path.

        Raises:
            SimulatorIncompatibleError: If UMLSL-Sim could not run the snapshot.
            CommandValidationError: If command validation fails.
        """
        if not self._file_path:
            raise CommandValidationError("File path is required to save a snapshot.")

        try:
            scenario_key = os.path.splitext(os.path.basename(self._file_path))[0]
            scenario = build_simulator_scenario(
                self._traffic_snapshot_reader.to_dict(), scenario_key, self._max_speed
            )
        except ValueError as exc:
            raise CommandValidationError(f"Failed to serialize snapshot: {exc}") from exc

        if not scenario.can_run:
            raise SimulatorIncompatibleError(scenario.errors)

        try:
            with open(self._file_path, "w", encoding="utf-8") as file:
                json.dump(scenario.payload, file, indent=2)
        except OSError as exc:
            raise CommandValidationError(f"Failed to save snapshot: {exc}") from exc
