from concurrent.futures import ProcessPoolExecutor

import networkx as nx

from umlsl_edit.model.domain_models.car_mixin import CarMixin

# Mixins
from umlsl_edit.model.domain_models.road_mixin import RoadMixin
from umlsl_edit.model.domain_models.segment_mixin import SegmentMixin
from umlsl_edit.model.domain_models.serialization_mixin import (
    SerializationMixin,
)
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_validator import (
    TrafficSnapshotValidator,
)
from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import Road
from umlsl_edit.model.helpers.event_types import (
    SettingsEventType,
)
from umlsl_edit.model.helpers.observables import (
    Observable,
    ObservableDict,
    ReadOnlyMergedDictView,
)
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.view.view_constants import DIMENSION


class TrafficSnapshotModel(
    Observable,
    # TrafficSnapshotReader,
    # TrafficSnapshotWriter,
    RoadMixin,
    CarMixin,
    SegmentMixin,
    SerializationMixin,
):
    """
    Represents the complete state of a traffic simulation.

    Serves as the single source of truth for all roads and cars. Implements both
    TrafficSnapshotReader and TrafficSnapshotWriter interfaces for read/write access.

    Uses Observable pattern to notify observers of changes without PySide dependencies.

    Events:
        - TrafficSnapshotEventType.CAR_ADDED: Fired when a car is added (data: Car)
        - TrafficSnapshotEventType.CAR_REMOVED: Fired when a car is removed (data: Car)
        - TrafficSnapshotEventType.CAR_UPDATED: Fired when a car is updated (data: Car)
        - TrafficSnapshotEventType.ROAD_ADDED: Fired when a road is added (data: Road)
        - TrafficSnapshotEventType.ROAD_REMOVED: Fired when a road is removed (data: Road)
        - TrafficSnapshotEventType.ROAD_UPDATED: Fired when a road is updated (data: Road)
    """

    def __init__(
            self,
            settings_model: SettingsModel,
            cars: ObservableDict[str, Car] | None = None,
    ):
        super().__init__()
        self.cars = (
            cars
            if cars is not None
            else ObservableDict[str, Car](
                on_add=self._on_car_added,
                on_remove=self._on_car_removed,
                on_update=self._on_car_updated,
            )
        )

        self._horizontal_roads: ObservableDict[str, Road] = ObservableDict(
            on_add=self._on_road_added,
            on_remove=self._on_road_removed,
            on_update=self._on_road_updated,
        )
        self._vertical_roads: ObservableDict[str, Road] = ObservableDict(
            on_add=self._on_road_added,
            on_remove=self._on_road_removed,
            on_update=self._on_road_updated,
        )
        self._segments: dict[str, Segment] = {}
        self._debug_segments: dict[str, Segment] = {}
        """Dictionary  of segments, keyed by their uid."""
        self._segments_by_lane: dict[Lane, list[str]] = {}
        """Dictionary mapping the lane to their corresponding segment uids."""
        self._graph = nx.DiGraph()
        """Graph representing the connectivity of segments."""

        self._read_only_roads = ReadOnlyMergedDictView(
            [self._horizontal_roads, self._vertical_roads]
        )
        """Read-only view of the roads dictionary."""

        self.lane_width = DIMENSION.LANE_WIDTH
        self.screen_size = (DIMENSION.SCENE_SIZE + 100) / 2

        self.validator = TrafficSnapshotValidator(self)
        self.settings_model: SettingsModel = settings_model
        self.settings_model.attach(self._on_settings_event)

        if not hasattr(TrafficSnapshotModel, '_shared_process_pool') or TrafficSnapshotModel._shared_process_pool is None:
            TrafficSnapshotModel._shared_process_pool = ProcessPoolExecutor(max_workers=2)
        self.process_pool = TrafficSnapshotModel._shared_process_pool
        self.evaluation_version = 0

    def get_scene_size(self) -> float:
        return self.screen_size

    def _on_settings_event(self, event_type: SettingsEventType, data=None) -> None:
        if event_type in (
                SettingsEventType.CHANGE_BRAKING_DECELERATION,
                SettingsEventType.CHANGE_MAX_SPEED,
        ):
            self._revalidate_cars()
