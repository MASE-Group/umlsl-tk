"""
The world extent: where the lanes of the snapshot end.

The editor's canvas is unbounded, but a lane with no crossing in some direction has to end somewhere. It ends at the
world extent: a rectangle centred on the origin that holds every road, every crossing and every car together with its
whole environment (view, reservation and claim), plus the view horizon H in each direction. H is the braking distance
of the settings, the distance a car's view reaches behind and ahead of it. The same rectangle is the canvas the
scenario gets in UMLSL-Sim, so the simulator's lanes end where the model checker's do.

A snapshot imported from UMLSL-Sim keeps the simulator's canvas instead, for as long as every road and every car body
still fits inside it. Its lanes then end at the canvas edges, where the simulator has its border crossings, and a view
that reaches an edge is cut there. That keeps Sim -> Edit -> Sim lossless, and the canvas the size a trained RL model
expects. Once a road or a car body leaves the canvas, the world is the extent described above, but never smaller than
the canvas; moving everything back inside returns to the canvas.

The extent is kept as half sizes ``(x, y)``, in lanes: the world is ``[-x, x] x [-y, y]``. A fitted extent is a whole
number of lanes, at least one.

Environments and the extent depend on each other: a view stops where its lane ends. ``_update_world_extent`` breaks the
cycle by building every environment with an extent that cannot cut any of them short, measuring them, and only then
fitting the extent to them. A view that does not reach the end of its lane is the same whatever the extent beyond it,
so fitting the extent changes no view; it only moves where the outer lane segments begin, which is why every
environment is rebuilt after the extent changes.
"""
import math
from typing import TYPE_CHECKING, Any, Iterable

from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.environment.helpers.environment_reach_helper import (
    environment_reach,
    lane_interval_reach,
)
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
    from umlsl_edit.model.entities.car import CarParams

WorldExtent = tuple[float, float]
"""Half width and half height of the world, in lanes."""

_EPSILON = 1e-9


def _ceil(value: float) -> float:
    # 9.000000000001 is a rounding error of 9, not a reason for a tenth lane
    return float(math.ceil(value - _EPSILON))


def _axis_of(orientation: RoadOrientation) -> int:
    """The axis a road of this orientation runs along: 0 for x, 1 for y."""
    return 0 if orientation == RoadOrientation.HORIZONTAL else 1


def _cross_section_reach(orientation: RoadOrientation, position: float, forward: int, backward: int,
                         lane_width: float) -> float:
    """How far from the origin a road reaches across its own direction."""
    if orientation == RoadOrientation.HORIZONTAL:
        low, high = position - forward * lane_width, position + backward * lane_width
    else:
        low, high = position - backward * lane_width, position + forward * lane_width
    return max(abs(low), abs(high))


def _extent_from(value: Any) -> WorldExtent | None:
    """A stored extent (a pair of numbers, or None)."""
    if value is None:
        return None
    return float(value[0]), float(value[1])


class WorldExtentMixin:
    def _init_world_extent(self: "TrafficSnapshotModel") -> None:
        self._simulator_canvas: WorldExtent | None = None
        self._world_extent: WorldExtent = self._fitted_extent((0.0, 0.0))
        self._reported_world_extent: WorldExtent = self._world_extent
        self._world_extent_frozen: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_world_extent(self: "TrafficSnapshotModel") -> WorldExtent:
        """Half width and half height of the world, in lanes: the lanes end at x = +-x and y = +-y."""
        return self._world_extent

    def get_simulator_canvas(self: "TrafficSnapshotModel") -> WorldExtent | None:
        """Half width and half height of the UMLSL-Sim canvas the snapshot was imported with, if it was."""
        return self._simulator_canvas

    def set_simulator_canvas(self: "TrafficSnapshotModel", canvas: WorldExtent | None) -> None:
        """Keep the world at this UMLSL-Sim canvas while everything fits inside it (``None``: no such canvas)."""
        self._simulator_canvas = None if canvas is None else (float(canvas[0]), float(canvas[1]))
        self._update_world_extent()

    def get_view_horizon(self: "TrafficSnapshotModel") -> float:
        """H: how far a car's view reaches behind and ahead of it, and the margin around everything in the world."""
        return self.settings_model.braking_distance()

    # ------------------------------------------------------------------
    # Bulk loading
    # ------------------------------------------------------------------

    def _begin_bulk_load(self: "TrafficSnapshotModel", data: dict[str, Any]) -> None:
        """
        Size the world for a whole payload before any of it is added, and hold the extent until ``_end_bulk_load``.

        A payload written by ``to_dict`` carries its world extent; one that does not gets an extent that cannot cut
        any of its environments short. Either way loading builds no environment for the extent's sake, and
        ``_end_bulk_load`` only rebuilds them if the payload's extent was not the fitted one.
        """
        self._world_extent_frozen += 1
        self._simulator_canvas = _extent_from(data.get("simulator_canvas"))
        stored = _extent_from(data.get("world_extent"))
        self._world_extent = stored if stored is not None else self._covering_extent_for_payload(data)

    def _end_bulk_load(self: "TrafficSnapshotModel") -> None:
        self._world_extent_frozen -= 1
        self._update_world_extent()

    def _abort_bulk_load(self: "TrafficSnapshotModel") -> None:
        """End a bulk load that failed: the snapshot is discarded, so there is nothing left to fit."""
        self._world_extent_frozen -= 1

    # ------------------------------------------------------------------
    # Keeping environments buildable
    # ------------------------------------------------------------------

    def _grow_world_extent(self: "TrafficSnapshotModel", needed: WorldExtent) -> bool:
        """Grow the extent to hold ``needed``. Returns whether it changed. Environments are left as they are."""
        grown = (
            self._world_extent[0] if needed[0] <= self._world_extent[0] else _ceil(needed[0]),
            self._world_extent[1] if needed[1] <= self._world_extent[1] else _ceil(needed[1]),
        )
        if grown == self._world_extent:
            return False
        self._world_extent = grown
        return True

    def _cover_car_params(self: "TrafficSnapshotModel", car_params: "CarParams") -> None:
        """
        Make sure the environment of a car with these parameters can be built: its body must lie inside the world.

        Called before a new or changed car's environment is built. If the world grows, the environments of the other
        cars are rebuilt, because their outer lane segments moved. Whether the new environment is cut short by the
        end of its lane is ``_update_world_extent``'s concern.
        """
        road = self.get_road_by_uid(car_params.lane.road_uid)
        needed = [0.0, 0.0]
        needed[_axis_of(road.orientation)] = abs(car_params.position_on_lane) + car_params.length
        if self._grow_world_extent((needed[0], needed[1])):
            self._rebuild_environments()

    def _cover_roads(self: "TrafficSnapshotModel") -> None:
        """
        Make sure every crossing and every car body lies inside the world, so that every environment can be built.

        Called after the roads changed and before the environments are rebuilt (which the caller does). A crossing
        outside the world would leave the outer lane segment next to it with a negative length.
        """
        needed = [0.0, 0.0]
        for axis, reach in self._road_reaches():
            needed[axis] = max(needed[axis], reach)
        for car in self.cars.values():
            if not self.is_road_existing(car.lane.road_uid):
                continue  # its road was just removed; revalidating the cars removes the car, too
            along = _axis_of(self.get_road_by_uid(car.lane.road_uid).orientation)
            needed[along] = max(needed[along], abs(car.position_on_lane) + car.length)
        self._grow_world_extent((needed[0], needed[1]))

    def _reach_margin(self: "TrafficSnapshotModel", extra_lengths: Iterable[float] = ()) -> float:
        """
        How far beyond a car's body, or beyond a crossing it drives through, its environment can reach along a lane.

        The view reaches H ahead of the car's rear and H behind it; a reservation reaches its braking distance (at most
        H) and the car's length ahead of the rear; and a space that ends inside a crossing is carried through it and
        one car length beyond. One lane on top keeps every such end strictly inside the world.
        """
        lengths = [car.length for car in self.cars.values()] + list(extra_lengths)
        return self.get_view_horizon() + 2.0 * max(lengths, default=0.0) + self.lane_width

    def _covering_extent(self: "TrafficSnapshotModel") -> WorldExtent:
        """An extent no environment of the current roads and cars can reach the end of."""
        margin = self._reach_margin()
        needed = [0.0, 0.0]
        for axis, reach in self._road_reaches():
            needed[axis] = max(needed[axis], reach + margin)
        for car in self.cars.values():
            along = _axis_of(self.get_road_by_uid(car.lane.road_uid).orientation)
            needed[along] = max(needed[along], abs(car.position_on_lane) + car.length + margin)
        return _ceil(needed[0]), _ceil(needed[1])

    def _covering_extent_for_payload(self: "TrafficSnapshotModel", data: dict[str, Any]) -> WorldExtent:
        """``_covering_extent`` for a ``to_dict`` payload that is not loaded yet."""
        roads = [r for r in data.get("roads", []) if isinstance(r, dict)]
        cars = [c for c in data.get("cars", []) if isinstance(c, dict)]
        margin = self._reach_margin(float(c.get("length", 0.0)) for c in cars)

        orientation_by_uid: dict[Any, RoadOrientation] = {}
        needed = [0.0, 0.0]
        for road in roads:
            raw = road.get("orientation")
            try:
                orientation = raw if isinstance(raw, RoadOrientation) else (
                    RoadOrientation[raw] if isinstance(raw, str) else RoadOrientation(raw))
                reach = _cross_section_reach(orientation, float(road["position"]),
                                             int(road["number_of_forward_lanes"]),
                                             int(road["number_of_backward_lanes"]), self.lane_width)
            except (KeyError, ValueError, TypeError):
                continue  # from_dict reports the malformed road
            orientation_by_uid[road.get("uid")] = orientation
            across = 1 - _axis_of(orientation)
            needed[across] = max(needed[across], reach + margin)
        for car in cars:
            orientation = orientation_by_uid.get(car.get("road_uid"))
            if orientation is None:
                continue
            try:
                reach = abs(float(car["position_on_lane"])) + float(car["length"]) + margin
            except (KeyError, ValueError, TypeError):
                continue
            along = _axis_of(orientation)
            needed[along] = max(needed[along], reach)
        return _ceil(needed[0]), _ceil(needed[1])

    def _rebuild_environments(self: "TrafficSnapshotModel") -> None:
        """Rebuild every car's environment for the current extent, without notifying anyone."""
        for car in self.cars.values():
            car.recalculate_environment(self, settings_model=self.settings_model)

    # ------------------------------------------------------------------
    # Measuring
    # ------------------------------------------------------------------

    def _road_reaches(self: "TrafficSnapshotModel") -> list[tuple[int, float]]:
        """For each road, the axis across it and how far from the origin it reaches along that axis."""
        return [
            (1 - _axis_of(road.orientation),
             _cross_section_reach(road.orientation, road.position, road.number_of_forward_lanes,
                                  road.number_of_backward_lanes, self.lane_width))
            for road in self.roads.values()
        ]

    def _body_reach(self: "TrafficSnapshotModel") -> WorldExtent:
        """How far from the origin the roads and the car bodies reach: what has to fit on a simulator canvas."""
        reach = [0.0, 0.0]
        for axis, road_reach in self._road_reaches():
            reach[axis] = max(reach[axis], road_reach)
        for car in self.cars.values():
            for segment_interval in car.environment.physical_segment_intervals:
                lane_reach = lane_interval_reach(self, segment_interval, car, False)
                if lane_reach is not None:
                    axis, low, high = lane_reach
                    reach[axis] = max(reach[axis], abs(low), abs(high))
        return reach[0], reach[1]

    def _environment_reach(self: "TrafficSnapshotModel") -> tuple[WorldExtent, bool]:
        """
        How far roads and environments reach from the origin, and whether some environment may have been cut short.

        An environment is cut short only at the end of its lane, so one that reaches the end of the world may be;
        one that ends before it is not.
        """
        reach = [0.0, 0.0]
        for axis, road_reach in self._road_reaches():
            reach[axis] = max(reach[axis], road_reach)

        may_be_cut_short = False
        horizon = self.get_view_horizon()
        for car in self.cars.values():
            car_reach = environment_reach(self, car)
            for axis in (0, 1):
                reach[axis] = max(reach[axis], car_reach[axis])
                if horizon > 0 and car_reach[axis] >= self._world_extent[axis] - _EPSILON:
                    may_be_cut_short = True
        return (reach[0], reach[1]), may_be_cut_short

    def _fitted_extent(self: "TrafficSnapshotModel", reach: WorldExtent) -> WorldExtent:
        horizon = self.get_view_horizon()
        minimum = self._simulator_canvas or (0.0, 0.0)
        return (
            max(_ceil(reach[0] + horizon), minimum[0], 1.0),
            max(_ceil(reach[1] + horizon), minimum[1], 1.0),
        )

    def _fits_simulator_canvas(self: "TrafficSnapshotModel") -> bool:
        if self._simulator_canvas is None:
            return False
        reach = self._body_reach()
        return all(reach[axis] <= self._simulator_canvas[axis] + _EPSILON for axis in (0, 1))

    # ------------------------------------------------------------------
    # Fitting the extent
    # ------------------------------------------------------------------

    def _set_extent_and_rebuild(self: "TrafficSnapshotModel", extent: WorldExtent) -> None:
        if extent != self._world_extent:
            self._world_extent = extent
            self._rebuild_environments()

    def _update_world_extent(self: "TrafficSnapshotModel") -> None:
        """
        Fit the extent to the roads and environments, rebuild the environments if it changed, and tell observers.

        Call it after every change of roads, cars or settings, once the environments are built.
        """
        if self._world_extent_frozen:
            return

        if self._fits_simulator_canvas():
            # an imported scenario that still fits keeps the simulator's canvas, cut-off views and all
            self._set_extent_and_rebuild(self._simulator_canvas)
        else:
            reach, may_be_cut_short = self._environment_reach()
            if may_be_cut_short:
                covering = self._covering_extent()
                self._set_extent_and_rebuild((max(self._world_extent[0], covering[0]),
                                              max(self._world_extent[1], covering[1])))
                reach, _ = self._environment_reach()
            self._set_extent_and_rebuild(self._fitted_extent(reach))

        if self._world_extent != self._reported_world_extent:
            self._reported_world_extent = self._world_extent
            self.notify(TrafficSnapshotEventType.WORLD_EXTENT_CHANGED, self._world_extent)
