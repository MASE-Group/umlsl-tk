"""Controller responsible for executing commands that modify the model."""

from typing import Optional

from umlsl_edit.commands.cars import add_car
from umlsl_edit.commands.cars.delete_car import DeleteCar
from umlsl_edit.commands.cars.edit_car import EditCarCommand
from umlsl_edit.commands.command import Command, CommandValidationError
from umlsl_edit.commands.persistence.export_snapshot import ExportSnapshot
from umlsl_edit.commands.persistence.import_snapshot import ImportSnapshot
from umlsl_edit.commands.persistence.load_traffic_snapshot import (
    LoadTrafficSnapshot,
)
from umlsl_edit.commands.persistence.save_as_traffic_snapshot import (
    SaveAsTrafficSnapshot,
)
from umlsl_edit.commands.persistence.save_traffic_snapshot import (
    SaveTrafficSnapshot,
)
from umlsl_edit.commands.roads import add_road, delete_road, edit_road
from umlsl_edit.commands.settings.change_braking_acceleration import (
    ChangeBrakingAccelerationCommand,
)
from umlsl_edit.commands.umlsl import (
    add_umlsl_query,
    delete_umlsl_query,
    edit_umlsl_query,
)
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)
from umlsl_edit.model.entities.car import Car, CarParams
from umlsl_edit.model.entities.road import Road, RoadOrientation, RoadParams
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery, UMLSLQueryParams
from umlsl_edit.model.errors.car_errors import (
    CarTrafficSnapshotContextValidationError,
)
from umlsl_edit.model.errors.road_errors import (
    RoadTrafficSnapshotContextValidationError,
)
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnIntent


class CommandController:
    """
    Manages command execution, validation.
    Provides high-level API for modifying the traffic snapshot.
    """

    def __init__(
            self,
            traffic_snapshot_reader: TrafficSnapshotReader,
            traffic_snapshot_writer: TrafficSnapshotWriter,
            umlsl_queries_model: UMLSLQueriesModel,
            settings_model: SettingsModel,
            application_controller: Optional[object] = None,
    ):
        """
        Initialize the command controller.

        Args:
            traffic_snapshot_reader: The model that will be modified by commands.
        """
        self.traffic_snapshot_reader = traffic_snapshot_reader
        self.traffic_snapshot_writer = traffic_snapshot_writer
        self.umlsl_queries_model = umlsl_queries_model
        self.settings_model = settings_model
        self._application_controller = application_controller
        self._current_snapshot_path: Optional[str] = None
        self._traffic_snapshot_changed_since_last_save = False
        # self._command_history = []  # TODO: Implement undo/redo stack
        # self._history_position = -1  # Current position in history

    def _execute_command(self, command: Command) -> None:
        """
        Executes a command with validation and potentially later adds it to the undo/redo history.

        Args:
            command: The command to execute.

        Returns:
            The return value from the command's execute() method.

        Raises:
            CommandValidationError: If the command fails validation.
        """
        self._preflight_snapshot_command(command)
        command.execute()

        if isinstance(
                command,
                (SaveTrafficSnapshot, SaveAsTrafficSnapshot, LoadTrafficSnapshot),
        ):
            # Saving and loading bring the snapshot back in sync with a file.
            self._set_snapshot_changed_since_last_save(False)
        elif isinstance(command, ExportSnapshot):
            # Exporting writes a separate interchange file and leaves the edited
            # snapshot untouched, so it must not affect the unsaved-changes flag.
            pass
        else:
            self._set_snapshot_changed_since_last_save(True)

    def _preflight_snapshot_command(self, command: Command) -> None:
        if not (
                hasattr(command, "_traffic_snapshot_reader")
                and hasattr(command, "_traffic_snapshot_writer")
        ):
            return
        if not isinstance(self.traffic_snapshot_reader, TrafficSnapshotModel):
            return

        snapshot_data = self.traffic_snapshot_reader.to_dict()
        clone_snapshot = TrafficSnapshotModel(self.settings_model)
        TrafficSnapshotModel.from_dict(
            snapshot_data, clone_snapshot, clone_snapshot, self.settings_model
        )

        original_reader = command._traffic_snapshot_reader
        original_writer = command._traffic_snapshot_writer
        try:
            command._traffic_snapshot_reader = clone_snapshot
            command._traffic_snapshot_writer = clone_snapshot
            command.execute()
        except Exception as exc:
            mapped_exc = self._map_preflight_exception(command, exc)
            if mapped_exc is not None:
                raise mapped_exc from exc
            raise
        finally:
            command._traffic_snapshot_reader = original_reader
            command._traffic_snapshot_writer = original_writer

    def _map_preflight_exception(
            self, command: Command, exc: Exception
    ) -> Exception | None:
        if isinstance(
                exc,
                (
                        CarTrafficSnapshotContextValidationError,
                        RoadTrafficSnapshotContextValidationError,
                ),
        ):
            return exc
        if isinstance(exc, ValueError):
            if isinstance(command, (add_car.AddCarCommand, EditCarCommand)):
                return CarTrafficSnapshotContextValidationError(content=str(exc))
            if isinstance(
                    command,
                    (
                            add_road.AddRoadCommand,
                            edit_road.EditRoadCommand,
                            delete_road.DeleteRoad,
                    ),
            ):
                return RoadTrafficSnapshotContextValidationError(content=str(exc))
        return None

    def _execute_without_history(self, command: Command) -> None:
        """
        Executes a command without adding it to the undo/redo history.
        Useful for ephemeral operations like selection changes.

        Args:
            command: The command to execute.

        Returns:
            The return value from the command's execute() method.

        Raises:
            CommandValidationError: If the command fails validation.
        """
        command.execute()

    def get_data_changed_since_last_save(self) -> bool:
        """
        Returns True if the traffic snapshot has been modified since the last save operation.
        """
        return self._traffic_snapshot_changed_since_last_save

    def _set_snapshot_changed_since_last_save(self, has_changes: bool) -> None:
        if self._traffic_snapshot_changed_since_last_save == has_changes:
            return

        self._traffic_snapshot_changed_since_last_save = has_changes

        if self._application_controller is None:
            return

        signal = self._application_controller.view_event_handler.get_on_snapshot_changed_signal()
        signal.emit(has_changes)

    # def undo(self) -> bool:
    #     """
    #     Undoes the last command in the history.
    #
    #     Returns:
    #         True if undo was successful, False if there's nothing to undo.
    #     """
    #     raise NotImplementedError("Method not implemented yet.")
    #
    # def redo(self) -> bool:
    #     """
    #     Redoes the next command in the history.
    #
    #     Returns:
    #         True if redo was successful, False if there's nothing to redo.
    #     """
    #     raise NotImplementedError("Method not implemented yet.")
    #
    # def can_undo(self) -> bool:
    #     """Returns True if there are commands to undo."""
    #     raise NotImplementedError("Method not implemented yet.")
    #
    # def can_redo(self) -> bool:
    #     """Returns True if there are commands to redo."""
    #     raise NotImplementedError("Method not implemented yet.")
    #
    # High-level command API methods

    def add_car(
            self,
            name: str,
            assigned_road: Road,
            lane_index: int,
            color: str,
            position_on_lane: float,
            transition: float,
            speed: float,
            length: float,
            acceleration: float,
            next_turn: Optional[TurnIntent],
    ) -> None:
        """
        Adds a car to the traffic snapshot based on the given parameters.

        Args:
            name: Unique human-readable identifier for the car.
            assigned_road: Reference to the Road the car is currently traveling on.
            lane_index: Index of the lane the car is currently in.
            color: Hex color code
            position_on_lane: Distance along lane
            transition: Lane change progress
            speed: Current speed
            length: Physical length
            acceleration: Current acceleration
            next_turn: Turn intent at intersection

        """
        lane = Lane(road_uid=assigned_road.uid, lane_index=lane_index)
        car_params = CarParams(
            name,
            lane,
            color,
            position_on_lane,
            transition,
            speed,
            length,
            next_turn,
            acceleration,
        )
        add_car_command = add_car.AddCarCommand(
            self.traffic_snapshot_reader,
            self.traffic_snapshot_writer,
            self.settings_model,
            car_params,
        )
        self._execute_command(add_car_command)

    def remove_car(self, car_uid: str) -> None:
        """
        Removes a car from the traffic snapshot.

        Args:
            car_uid: The unique identifier of the car to remove.

        """
        remove_car_command = DeleteCar(
            self.traffic_snapshot_writer, self.traffic_snapshot_reader, car_uid
        )
        self._execute_command(remove_car_command)

    _UNCHANGED = object()

    def edit_car(
            self,
            car: Car,
            car_name: object = _UNCHANGED,
            road_uid: object = _UNCHANGED,
            lane_index: object = _UNCHANGED,
            color: object = _UNCHANGED,
            position_on_lane: object = _UNCHANGED,
            transition: object = _UNCHANGED,
            speed: object = _UNCHANGED,
            length: object = _UNCHANGED,
            next_turn: object = _UNCHANGED,
            acceleration: object = _UNCHANGED,
    ) -> None:
        """
        Edits properties of an existing car using a merge strategy:
        any parameter left as _UNCHANGED keeps the current value.
        Passing next_turn=None explicitly clears it.
        """

        if road_uid is self._UNCHANGED and lane_index is self._UNCHANGED:
            lane = car.lane
        else:
            road_uid = car.lane.road_uid if road_uid is self._UNCHANGED else road_uid
            lane_index = (
                car.lane.lane_index if lane_index is self._UNCHANGED else lane_index
            )
            lane = Lane(road_uid=road_uid, lane_index=lane_index)

        car_params = CarParams(
            name=car.name if car_name is self._UNCHANGED else car_name,
            lane=lane,
            color=car.color if color is self._UNCHANGED else color,
            position_on_lane=car.position_on_lane
            if position_on_lane is self._UNCHANGED
            else position_on_lane,
            transition=car.transition if transition is self._UNCHANGED else transition,
            speed=car.speed if speed is self._UNCHANGED else speed,
            length=car.length if length is self._UNCHANGED else length,
            next_turn=car.next_turn if next_turn is self._UNCHANGED else next_turn,
            acceleration=car.acceleration
            if acceleration is self._UNCHANGED
            else acceleration,
        )

        edit_car_command = EditCarCommand(
            self.traffic_snapshot_reader,
            self.traffic_snapshot_writer,
            car_params,
            car.uid,
        )
        self._execute_command(edit_car_command)

    def add_road(
            self,
            name: str,
            orientation: RoadOrientation,
            position: float,
            number_of_forward_lanes: int,
            number_of_backward_lanes: int,
    ) -> None:
        """
        Adds a road to the traffic snapshot based on the given parameters.

        Args:
            name: Unique human-readable identifier for the road.
            orientation: The orientation of the road (horizontal or vertical).
            position: The position of the road in the coordinate system.
            number_of_forward_lanes: Number of lanes in the forward direction.
            number_of_backward_lanes: Number of lanes in the backward direction.
        """
        road_params = RoadParams(
            name,
            orientation,
            position,
            number_of_forward_lanes,
            number_of_backward_lanes,
        )
        add_road_command = add_road.AddRoadCommand(
            self.traffic_snapshot_reader, self.traffic_snapshot_writer, road_params
        )
        self._execute_command(add_road_command)

    def remove_road(self, road_uid: str) -> None:
        """
        Removes a road from the traffic snapshot.

        Args:
            road_uid: The unique identifier of the road to remove.
        """
        remove_road_command = delete_road.DeleteRoad(
            self.traffic_snapshot_writer, self.traffic_snapshot_reader, road_uid
        )
        self._execute_command(remove_road_command)

    def update_road(
            self,
            road: Road,
            name: object = _UNCHANGED,
            orientation: object = _UNCHANGED,
            position: object = _UNCHANGED,
            number_of_forward_lanes: object = _UNCHANGED,
            number_of_backward_lanes: object = _UNCHANGED,
    ) -> None:
        """
        Updates an existing road using a merge strategy.
        """
        road_params = RoadParams(
            name=road.name if name is self._UNCHANGED else name,
            orientation=road.orientation
            if orientation is self._UNCHANGED
            else orientation,
            position=road.position if position is self._UNCHANGED else position,
            number_of_forward_lanes=road.number_of_forward_lanes
            if number_of_forward_lanes is self._UNCHANGED
            else number_of_forward_lanes,
            number_of_backward_lanes=road.number_of_backward_lanes
            if number_of_backward_lanes is self._UNCHANGED
            else number_of_backward_lanes,
        )

        edit_road_command = edit_road.EditRoadCommand(
            self.traffic_snapshot_reader,
            self.traffic_snapshot_writer,
            road_params,
            road.uid,
        )
        self._execute_command(edit_road_command)

    def add_umlsl_query(
            self, assigned_car_uid: str, should_only_evaluate_on_cars_lane: bool, latex: str
    ) -> None:
        """
        Adds a UMLSL query associated with a car.

        Args:
            assigned_car_uid: The car this query is assigned to.
            latex: The LaTeX representation of the query.
        """
        umlsl_query_params = UMLSLQueryParams(
            latex, assigned_car_uid, should_only_evaluate_on_cars_lane
        )
        add_umlsl_query_command = add_umlsl_query.AddUMLSLQuery(
            umlsl_query_params, self.umlsl_queries_model, self.traffic_snapshot_reader
        )
        self._execute_command(add_umlsl_query_command)

    def remove_umlsl_query(self, query_id: str) -> None:
        """
        Removes a UMLSL query.

        Args:
            query_id: The unique identifier of the query to remove.
        """
        remove_umlsl_query_command = delete_umlsl_query.DeleteUMLSLQuery(
            query_id, self.umlsl_queries_model
        )
        self._execute_command(remove_umlsl_query_command)

    def update_umlsl_query(
            self,
            query: UMLSLQuery,
            assigned_car_name: object = _UNCHANGED,
            should_only_evaluate_on_cars_lane: object = _UNCHANGED,
            latex: object = _UNCHANGED,
    ) -> None:
        """
        Edits an existing UMLSL query using a merge strategy.

        Args:
            query: The query object to edit.
            assigned_car_name: New assigned car name (optional).
            latex: New LaTeX string (optional).
        """
        umlsl_query_params = UMLSLQueryParams(
            latex=query.latex if latex is self._UNCHANGED else latex,
            assigned_car_uid=query.assigned_car_uid
            if assigned_car_name is self._UNCHANGED
            else assigned_car_name,
            should_only_evaluate_on_cars_lane=query.should_only_evaluate_on_cars_lane
            if should_only_evaluate_on_cars_lane is self._UNCHANGED
            else should_only_evaluate_on_cars_lane,
        )
        edit_umlsl_query_command = edit_umlsl_query.EditUMLSLQuery(
            query.uid, umlsl_query_params, self.umlsl_queries_model
        )
        self._execute_command(edit_umlsl_query_command)

    # todo correct skeletons for load/save traffic snapshot
    def get_current_snapshot_path(self) -> Optional[str]:
        return self._current_snapshot_path

    def set_current_snapshot_path(self, file_path: Optional[str]) -> None:
        self._current_snapshot_path = file_path

        if self._application_controller is None:
            return

        signal = self._application_controller.view_event_handler.get_on_snapshot_changed_signal()
        signal.emit(self._traffic_snapshot_changed_since_last_save)

    def load_traffic_snapshot(self, file_path: str) -> None:
        """
        Loads a traffic snapshot from the specified file path.
        """
        if not file_path:
            raise CommandValidationError("File path is required to load a snapshot.")
        if self._application_controller is None:
            raise CommandValidationError(
                "Application controller is required to load a snapshot."
            )
        load_command = LoadTrafficSnapshot(file_path, self._application_controller)
        self._execute_command(load_command)
        # A file in the UMLSL-Sim interchange format is treated like an import:
        # keeping its path would make 'Save' overwrite a simulator scenario with
        # native editor JSON, so the user is sent through 'Save As' instead.
        self.set_current_snapshot_path(None if load_command.loaded_external else file_path)

    def save_traffic_snapshot(self) -> None:
        """
        Saves the current traffic snapshot to the last known file path.
        """
        if not self._current_snapshot_path:
            raise CommandValidationError(
                "No snapshot file path is set. Use Save As first."
            )
        save_command = SaveTrafficSnapshot(
            self._current_snapshot_path,
            self.traffic_snapshot_reader,
            self.umlsl_queries_model,
        )
        self._execute_command(save_command)

    def save_as_traffic_snapshot(self, file_path: str) -> None:
        """
        Saves the current traffic snapshot to the specified file path.
        """
        if not file_path:
            raise CommandValidationError("File path is required to save a snapshot.")
        save_command = SaveAsTrafficSnapshot(
            file_path,
            self.traffic_snapshot_reader,
            self.umlsl_queries_model,
        )
        self._execute_command(save_command)
        self.set_current_snapshot_path(file_path)

    def export_snapshot(self, file_path: str) -> None:
        """
        Exports the current traffic snapshot to the specified file path.
        """
        if not file_path:
            raise CommandValidationError("File path is required to export a snapshot.")
        export_command = ExportSnapshot(
            file_path,
            self.traffic_snapshot_reader,
        )
        self._execute_command(export_command)

    def import_snapshot(self, file_path: str) -> None:
        """
        Imports a traffic snapshot from the specified file path.
        """
        if not file_path:
            raise CommandValidationError("File path is required to import a snapshot.")
        load_command = ImportSnapshot(
            file_path,
            self._application_controller
        )
        self._execute_command(load_command)
        # An imported snapshot has no native file behind it. Clearing the path
        # sends the next 'Save' through 'Save As', so native editor JSON can
        # never be written over the file that was open before the import.
        self.set_current_snapshot_path(None)

    def change_braking_acceleration(self, value: float) -> None:
        """
        Changes the braking acceleration of the cars.
        """
        change_braking_acceleration_command = ChangeBrakingAccelerationCommand(
            self.settings_model, value
        )
        self._execute_command(change_braking_acceleration_command)
