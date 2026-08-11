"""
Facade controller that combines ViewController and CommandController.
Provides a unified interface for the application's controller layer.
"""

from umlsl_edit.controllers.command_controller import CommandController
from umlsl_edit.controllers.data_controller import DataController
from umlsl_edit.controllers.event_controller import EventController
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
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType
from umlsl_edit.view.view_event_handler_impl import (
    ViewEventHandlerImplementation,
)
from umlsl_edit.view.view_models import ViewModels


class ApplicationController:
    """
    Main application controller that delegates responsibilities to specialized controllers:
    - ViewController: Handles model-to-view synchronization
    - CommandController: Handles command execution and undo/redo
    """

    def __init__(self):
        """
        Initialize the application controller with its sub-controllers.
        """
        self._model_view = ViewModels(self)
        self._settings_model = SettingsModel(
            braking_acceleration=8.0, max_speed=15)
        self._model_traffic_snapshot = TrafficSnapshotModel(self._settings_model)
        self._model_umlsl_queries = UMLSLQueriesModel(self._model_traffic_snapshot)
        self.view_event_handler = ViewEventHandlerImplementation(self._model_view)

        self._model_view.connect_signals(self.view_event_handler)

        self.event_controller = EventController(traffic_snapshot=self._model_traffic_snapshot,
                                                view=self.view_event_handler, settings=self._settings_model,
                                                umlsl_queries=self._model_umlsl_queries)
        self.command_controller = CommandController(traffic_snapshot_reader=self._model_traffic_snapshot,
                                                    traffic_snapshot_writer=self._model_traffic_snapshot,
                                                    settings_model=self._settings_model,
                                                    umlsl_queries_model=self._model_umlsl_queries,
                                                    application_controller=self)
        self.data_controller = DataController(traffic_snapshot_reader=self._model_traffic_snapshot)

    def get_traffic_snapshot_reader(self) -> TrafficSnapshotReader:
        return self._model_traffic_snapshot

    def get_traffic_snapshot_writer(self) -> TrafficSnapshotWriter:
        return self._model_traffic_snapshot

    def get_settings_model(self) -> SettingsModel:
        return self._settings_model

    def replace_snapshot(
            self,
            traffic_snapshot: TrafficSnapshotModel,
            umlsl_queries: UMLSLQueriesModel
    ) -> None:
        """
        Replace snapshot and queries across all controllers and emit a bulk reload event.

        Args:
            traffic_snapshot: The new traffic snapshot model.
            umlsl_queries: The new UMLSL queries model.
        """
        self._model_traffic_snapshot = traffic_snapshot
        self._model_umlsl_queries = umlsl_queries

        self.command_controller.traffic_snapshot_reader = traffic_snapshot
        self.command_controller.traffic_snapshot_writer = traffic_snapshot
        self.command_controller.umlsl_queries_model = umlsl_queries

        self.data_controller.replace_snapshot_reader(traffic_snapshot)
        self.event_controller.replace_models(traffic_snapshot, umlsl_queries)

        self._model_traffic_snapshot.notify(
            TrafficSnapshotEventType.SNAPSHOT_RELOADED,
            {"snapshot": traffic_snapshot, "queries": umlsl_queries},
        )
