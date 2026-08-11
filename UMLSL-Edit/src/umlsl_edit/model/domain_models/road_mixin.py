from typing import TYPE_CHECKING
from umlsl_edit.model.entities.road import Road, RoadOrientation, RoadParams
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel

class RoadMixin:
    def is_road_existing(self: "TrafficSnapshotModel", uid: str) -> bool:
        if uid in self._horizontal_roads or uid in self._vertical_roads:
            return True
        return False

    def validate_road_params(
            self: "TrafficSnapshotModel",
            road_params: RoadParams,
            new_instantiation: bool,
            road_uid: str | None = None,
    ) -> None:
        if (
                not new_instantiation
                and road_uid is None
                or new_instantiation
                and road_uid is not None
        ):
            raise ValueError("road_uid must be None for new road instantiation.")
        self.validator.validate_road_params(road_params, new_instantiation, road_uid)

    def get_lane_width(self: "TrafficSnapshotModel"):
        """Get the width of a single lane in the traffic snapshot.

        Returns:
            The width of a lane as a float.
        """
        return self.lane_width

    def get_road_by_uid(self: "TrafficSnapshotModel", uid: str) -> Road:
        """Retrieve a road by its unique identifier (uid).

        Args:
            uid: The unique identifier of the road.

        Returns:
            The Road object if found.

        Raises:
            ValueError: If the road does not exist in the snapshot.
        """
        if uid in self._horizontal_roads:
            return self._horizontal_roads[uid]
        elif uid in self._vertical_roads:
            return self._vertical_roads[uid]
        raise ValueError(f"Road with uid {uid} not found.")

    @property
    def roads(self: "TrafficSnapshotModel"):
        return self._read_only_roads

    def _on_road_added(self: "TrafficSnapshotModel", road: Road):
        self._recalculate_static_segments()
        self._revalidate_cars()
        # self.revalidate_queries()
        self.notify(TrafficSnapshotEventType.ROAD_ADDED, road)

    def _on_road_removed(self: "TrafficSnapshotModel", road: Road):
        # Recalculate segments BEFORE notifying observers to ensure consistency.
        # This prevents observers from accessing stale segments that reference the removed road.
        self._recalculate_static_segments()
        self._revalidate_cars()
        # self.revalidate_queries()
        self.notify(TrafficSnapshotEventType.ROAD_REMOVED, road)

    def _on_road_updated(self: "TrafficSnapshotModel", road: Road):
        self._recalculate_static_segments()
        self._revalidate_cars()
        # self.revalidate_queries()
        self.notify(TrafficSnapshotEventType.ROAD_UPDATED, road)

    def get_roads(self: "TrafficSnapshotModel") -> dict[str, Road]:
        return {**self._horizontal_roads, **self._vertical_roads}

    def validate_lane(self: "TrafficSnapshotModel", road: Road, lane_index: int, lane_direction: str) -> bool:
        """
        Validates if the specified lane index and direction exist on the given road.

        Args:
            road: The road to validate against.
            lane_index: The index of the lane to validate (0-based within the direction).
            lane_direction: The direction of the lane to validate ('fn' for forward, 'bn' for backward).

        Returns:
            True if the lane index and direction are valid for the road, False otherwise.
        """
        if not isinstance(road, Road):
            return False
        if not isinstance(lane_index, int):
            return False
        if not isinstance(lane_direction, str):
            return False

        normalized = lane_direction.strip().lower()
        if normalized in {"fn", "forward"}:
            return 0 <= lane_index < road.number_of_forward_lanes
        if normalized in {"bn", "backward"}:
            return 0 <= lane_index < road.number_of_backward_lanes
        return False

    def add_road(self: "TrafficSnapshotModel", road: Road) -> None:
        road_params = RoadParams(
            name=road.name,
            orientation=road.orientation,
            position=road.position,
            number_of_forward_lanes=road.number_of_forward_lanes,
            number_of_backward_lanes=road.number_of_backward_lanes,
        )
        self.validate_road_params(road_params, True)
        if self.is_road_existing(road.uid):
            raise ValueError(f"Road with uid {road.uid} already exists.")
        if road.orientation == RoadOrientation.HORIZONTAL:
            self._horizontal_roads[road.uid] = road
        else:
            self._vertical_roads[road.uid] = road

    def remove_road(self: "TrafficSnapshotModel", road_uid: str) -> None:
        if road_uid in self._horizontal_roads:
            self._horizontal_roads.pop(road_uid)
        elif road_uid in self._vertical_roads:
            self._vertical_roads.pop(road_uid)

    def update_road(self: "TrafficSnapshotModel", road_uid: str, road_params: RoadParams) -> None:
        self.validate_road_params(road_params, False, road_uid)
        road = self.get_road_by_uid(road_uid)
        original_orientation = road.orientation

        road.update_from_params(road_params)

        if original_orientation != road.orientation:
            if original_orientation == RoadOrientation.HORIZONTAL:
                if road_uid in self._horizontal_roads._data:
                    del self._horizontal_roads._data[road_uid]
                self._vertical_roads._data[road_uid] = road
            else:
                if road_uid in self._vertical_roads._data:
                    del self._vertical_roads._data[road_uid]
                self._horizontal_roads._data[road_uid] = road
            self._on_road_updated(road)
        else:
            if road.orientation == RoadOrientation.HORIZONTAL:
                self._horizontal_roads[road_uid] = road
            else:
                self._vertical_roads[road_uid] = road
