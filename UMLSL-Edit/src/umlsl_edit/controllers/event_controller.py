"""Controller responsible for synchronizing the model state to the view layer."""
from enum import Enum

from umlsl_edit.controllers.view_event_contract import ViewEventHandler
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel
from umlsl_edit.model.helpers.event_types import (
    TrafficSnapshotEventType,
    SettingsEventType,
    UMLSLQueriesEventType
)


class EventController:
    """
    Connects TrafficSnapshot model events to TrafficView methods.
    Handles all model-to-view synchronization without intermediate logic.
    Uses Observable pattern instead of PySide signals for backend independence.
    """

    def __init__(self,
                 view: ViewEventHandler,
                 traffic_snapshot: TrafficSnapshotModel,
                 settings: SettingsModel,
                 umlsl_queries: UMLSLQueriesModel) -> None:
        """
        Initialize the view controller.

        Args:
            view: The view that implements ViewEventHandler interface.
            traffic_snapshot: The model that notifies observers when data changes.
            settings: The settings model that notifies observers when settings change.
            umlsl_queries: The UMLSL queries model that notifies observers when queries change.
        """
        self._traffic_snapshot = traffic_snapshot
        self._view = view
        self._settings = settings
        self._umlsl_queries = umlsl_queries
        self._setup_event_listeners()

    def _setup_event_listeners(self) -> None:
        """
        Connects TrafficSnapshot events to TrafficView methods using Observable pattern.
        """
        self._traffic_snapshot.attach(self._on_traffic_snapshot_event)
        self._settings.attach(self._on_settings_event)
        self._umlsl_queries.attach(self._on_umlsl_query_event)

    def replace_models(
            self,
            traffic_snapshot: TrafficSnapshotModel,
            umlsl_queries: UMLSLQueriesModel
    ) -> None:
        """
        Swap the underlying models and rewire event listeners.
        """
        self._traffic_snapshot.detach(self._on_traffic_snapshot_event)
        self._umlsl_queries.detach(self._on_umlsl_query_event)

        self._traffic_snapshot = traffic_snapshot
        self._umlsl_queries = umlsl_queries

        self._traffic_snapshot.attach(self._on_traffic_snapshot_event)
        self._umlsl_queries.attach(self._on_umlsl_query_event)

    def _on_traffic_snapshot_event(self, event_type: Enum, data) -> None:
        """
        Handle events from the traffic snapshot model.

        Args:
            event_type: The type of event (TrafficSnapshotEventType enum)
            data: The data associated with the event (Car, Road, CrossingSegment, etc.)
        """
        # Route events to appropriate view methods
        if event_type == TrafficSnapshotEventType.CAR_ADDED:
            self._view.add_car_view(data)
        elif event_type == TrafficSnapshotEventType.CAR_REMOVED:
            self._view.remove_car_view(data)
        elif event_type == TrafficSnapshotEventType.CAR_UPDATED:
            self._view.update_car_view(data)
        elif event_type == TrafficSnapshotEventType.ROAD_ADDED:
            self._view.add_road_view(data)
        elif event_type == TrafficSnapshotEventType.ROAD_REMOVED:
            self._view.remove_road_view(data)
        elif event_type == TrafficSnapshotEventType.ROAD_UPDATED:
            self._view.update_road_view(data)
        elif event_type == TrafficSnapshotEventType.SNAPSHOT_RELOADED:
            if hasattr(self._view, "on_snapshot_reloaded"):
                if isinstance(data, dict):
                    self._view.on_snapshot_reloaded(data.get("snapshot"), data.get("queries"))
                else:
                    self._view.on_snapshot_reloaded(data, None)
        # elif event_type == TrafficSnapshotEventType.CROSSING_SEGMENT_ADDED:
        #     self._view.add_crossing_segment_view(data)
        # elif event_type == TrafficSnapshotEventType.CROSSING_SEGMENT_REMOVED:
        #     self._view.remove_crossing_segment_view(data)
        # elif event_type == TrafficSnapshotEventType.CROSSING_SEGMENT_UPDATED:
        #     self._view.update_crossing_segment_view(data)
        # elif event_type == TrafficSnapshotEventType.TRAFFIC_SNAPSHOT_WARNING:
        #     self._view.display_warning(data)
        # elif event_type == TrafficSnapshotEventType.SEGMENTS_RECALCULATED:
        #     self._view.refresh_all_segments_view(data)

    def _on_settings_event(self, event_type: Enum, data) -> None:
        """
        Handle events from the settings model.

        Args:
            event_type: The type of event (SettingsEventType enum)
            data: The data associated with the event
        """
        # Route events to appropriate view methods
        if event_type == SettingsEventType.CHANGE_BRAKING_DECELERATION:
            pass
        elif event_type == SettingsEventType.CHANGE_MAX_SPEED:
            pass

    def _on_umlsl_query_event(self, event_type: Enum, data) -> None:
        """
        Handle events from the UMLSL queries model.

        Args:
            event_type: The type of event (UMLSLQueriesEventType enum)
            data: The data associated with the event (UMLSLQuery)
        """
        # Route events to appropriate view methods
        if event_type == UMLSLQueriesEventType.UMLSL_QUERY_ADDED:
            self._view.add_query_view(data)
            # self._traffic_snapshot.revalidate_queries()
        elif event_type == UMLSLQueriesEventType.UMLSL_QUERY_REMOVED:
            self._view.remove_query_view(data)
        elif event_type == UMLSLQueriesEventType.UMLSL_QUERY_UPDATED:
            self._view.update_query_view(data)
        elif event_type == UMLSLQueriesEventType.UMLSL_QUERY_LOADING:
            self._view.loading_query_view(data)
