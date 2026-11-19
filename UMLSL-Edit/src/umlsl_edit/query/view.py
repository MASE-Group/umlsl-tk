from typing import TYPE_CHECKING, TypeVar, Generic, Callable

from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import SegmentInterval
from umlsl_edit.model.traffic_value_objects.segments.virtual_lane import VirtualLane

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import Car

T = TypeVar('T')


class LazyEvaluator(Generic[T]):
    """
    Lazy evaluates data if acquired. Once the data is acquired, it is cached and reused.
    """

    def __init__(self, data: T, on_update: Callable[[T], T]):
        self.data = data
        self.updated = False
        self.on_update = on_update

    def acquire_data(self) -> T:
        """
        Acquires the data. Returns the cached data if already acquired. Otherwise, calls the on_update function.
        """
        if not self.updated:
            self.data = self.on_update(self.data)
            self.updated = True
        return self.data


class View:
    """
    The View holds the virtual lanes and segments that are currently visible in the horizon, as well as the ego car.
    Additionally, we store the visible cars, reserved segments, claimed segments. Note that they are passed through
    the View and are lazily evaluated (only when needed) and cached for that View. The cache *for another* View is
    invalidated on chop operations.
    For example, if there are multiple accesses on the visible cars inside a View, we only compute the visible cars once.
    If there is a chop operation, only the cache of the *newly created* View is invalidated (since the visibility
    changes there); and is only recomputed in the newly created View when needed.
    """

    # A chop builds two Views per candidate split, so they are kept small: no per-instance dict, and the
    # lazily filtered data in plain fields rather than in a LazyEvaluator with a closure each.
    __slots__ = (
        "_virtual_lanes", "_segments_in_view", "_unfiltered_lanes",
        "horizon", "ego", "cars_in_view", "lane_range", "memo",
        "_visible_cars", "_reserved_segments", "_claimed_segments",
        "_visible_cars_filtered", "_reserved_segments_filtered", "_claimed_segments_filtered",
    )

    def __init__(self, virtual_lanes: list[VirtualLane] | None, segments_in_view: list[SegmentInterval] | None,
                 horizon: Interval, ego: 'Car',
                 visible_cars: dict[str, dict[SegmentInterval, Interval]],
                 reserved_segments: dict[str, dict[SegmentInterval, Interval]],
                 claimed_segments: dict[str, dict[SegmentInterval, Interval]],
                 cars_in_view: list[str],
                 lane_range: tuple[int, int] | None = None,
                 memo: dict | None = None,
                 unfiltered_lanes: list[VirtualLane] | None = None,
                 ):
        # A chopped View is given the lanes it was chopped from (`unfiltered_lanes`) instead of its own,
        # and filters them to its horizon only when its lanes or segments are first asked for: many
        # observed spaces are never looked at (a `true` operand, a length comparison).
        self._virtual_lanes = virtual_lanes
        self._segments_in_view = segments_in_view
        self._unfiltered_lanes = unfiltered_lanes
        self.horizon = horizon
        self.ego = ego
        # the cars (uids) whose reservation or claim overlaps ego's whole view, which the quantifiers
        # range over in every observed space; unlike the other data, it does not shrink on chops
        self.cars_in_view = cars_in_view

        # Below the root, an observed space is determined by its horizon and by the slice of the root's
        # virtual lanes it spans: a horizontal chop keeps the slice and filters the lanes' segments by
        # the new horizon, a vertical chop keeps the horizon and narrows the slice, and filtering by a
        # horizon after filtering by a wider one is the same as filtering by it alone. The root is
        # built differently (its lanes are not filtered), so its lane_range is None, which no chopped
        # View has. `memo` is shared by every View chopped from the same root, so a subformula decided
        # on an observed space is not decided again when another chop reaches the same space (see
        # HorizontalChopNode).
        self.lane_range = lane_range
        self.memo = {} if memo is None else memo

        # the data as passed in until it is first asked for, then filtered to this View (see get_*)
        self._visible_cars = visible_cars
        self._reserved_segments = reserved_segments
        self._claimed_segments = claimed_segments
        self._visible_cars_filtered = False
        self._reserved_segments_filtered = False
        self._claimed_segments_filtered = False

    def chop_horizontally(self, split: float) -> tuple['View', 'View']:
        """
        Chops the View horizontally at the given split value. That means the horizon is split into two parts (at the
        given value) and the two parts are returned as two separate Views.

        Returns:
            left, right: where left is the left View and right is the right View
        """
        lanes = self._lanes_to_chop()
        lane_range = self.lane_range or (0, len(lanes))

        left_horizon = Interval(self.horizon.start, split)
        left_view = self._construct_view(left_horizon, lanes, lane_range)

        right_horizon = Interval(split, self.horizon.end)
        right_view = self._construct_view(right_horizon, lanes, lane_range)

        return left_view, right_view

    def chop_vertically(self, split: int) -> tuple['View', 'View']:
        """
        Chops the View vertically at the given split index. That means the virtual lanes are split into two parts (the
        lower and upper part) and the two parts are returned as two separate Views.

        Returns:
            lower, upper: where lower is the lower View and upper is the upper View
        """
        # the slice of the root's virtual lanes each part spans; the root spans all of them
        lanes = self._lanes_to_chop()
        low, high = self.lane_range or (0, len(lanes))

        lower_lanes = lanes[:split]  # take all lanes whose index is < split_index
        middle = low + len(lower_lanes)
        lower_view = self._construct_view(self.horizon, lower_lanes, (low, middle))

        upper_lanes = lanes[split:]
        upper_view = self._construct_view(self.horizon, upper_lanes, (middle, high))

        return lower_view, upper_view

    @property
    def virtual_lanes(self) -> list[VirtualLane]:
        if self._virtual_lanes is None:
            self._filter_lanes()
        return self._virtual_lanes

    @property
    def segments_in_view(self) -> list[SegmentInterval]:
        if self._segments_in_view is None:
            self._filter_lanes()
        return self._segments_in_view

    def _lanes_to_chop(self) -> list[VirtualLane]:
        """
        The lanes the parts of a chop filter to their horizons: this View's own if it has filtered them,
        otherwise the ones it was chopped from. Both give the parts the same lanes, since filtering keeps
        every lane (an empty one too) and filtering by a horizon after filtering by a wider one is the
        same as filtering by it alone.
        """
        return self._unfiltered_lanes if self._virtual_lanes is None else self._virtual_lanes

    def _filter_lanes(self) -> None:
        segments_in_view: list[SegmentInterval] = []
        new_virtual_lanes: list[VirtualLane] = []
        start, end = self.horizon.start, self.horizon.end

        for virtual_lane in self._unfiltered_lanes:
            new_virtual_lane = []

            for segment_interval in virtual_lane.segment_intervals:
                # only take those segments that overlap the horizon; a segment that merely touches it
                # at an endpoint shares no space with it. This is the positive length of
                # horizon.intersection(interval), without building the intersection.
                interval = segment_interval.interval
                if min(end, interval.end) - max(start, interval.start) > 0:
                    segments_in_view.append(segment_interval)
                    new_virtual_lane.append(segment_interval)

            # the lane stays part of the observed space even where it has no segment (a virtual lane
            # may end before the horizon does), so that atoms still see how many lanes it spans
            new_virtual_lanes.append(VirtualLane(new_virtual_lane))

        self._virtual_lanes = new_virtual_lanes
        self._segments_in_view = segments_in_view
        self._unfiltered_lanes = None

    def _construct_view(self, horizon: Interval, lanes: list[VirtualLane], lane_range: tuple[int, int]) -> 'View':
        return View(
            None,
            None,
            horizon,
            self.ego,
            # filtered already if this View was asked for it, otherwise as passed in to this View
            self._visible_cars,
            self._reserved_segments,
            self._claimed_segments,
            self.cars_in_view,
            lane_range,
            self.memo,
            lanes,
        )

    def _compute_visible_cars_in_view(self, old_cars: dict[str, dict[SegmentInterval, Interval]]):
        # only consider cars that intersect with the horizon
        updated_visible_cars: dict[str, dict[SegmentInterval, Interval]] = dict()
        segments_in_view = self.segments_in_view
        start, end = self.horizon.start, self.horizon.end
        for intersecting_car, occupied_segment_interval in old_cars.items():
            # if there is any intersection with the horizon, we can put all the occupied segments of the car in the view
            # this won't break the logic and safes us computation time. The interval test is
            # occupied_interval.intersects(self.horizon), without building the intersection.
            any_intersects = any(
                occupied_segment in segments_in_view
                and max(occupied_interval.start, start) <= min(occupied_interval.end, end)
                for occupied_segment, occupied_interval in occupied_segment_interval.items()
            )
            if any_intersects:
                updated_visible_cars[intersecting_car] = occupied_segment_interval

        return updated_visible_cars

    def _compute_reserved_segments_in_view(self, old_reserved_segments: dict[str, dict[SegmentInterval, Interval]]):
        return self._recompute_segments_in_view(old_reserved_segments)

    def _compute_claimed_segments_in_view(self, old_claimed_segments: dict[str, dict[SegmentInterval, Interval]]):
        return self._recompute_segments_in_view(old_claimed_segments)

    def _recompute_segments_in_view(self, old_segments: dict[str, dict[SegmentInterval, Interval]]):
        new_segments: dict[str, dict[SegmentInterval, Interval]] = dict()
        segments_in_view = self.segments_in_view
        start, end = self.horizon.start, self.horizon.end
        for car, reserved_segments in old_segments.items():
            new_car_segments: dict[SegmentInterval, Interval] = dict()
            for segment, interval in reserved_segments.items():
                # self.horizon.intersects(interval), without building the intersection
                if segment in segments_in_view and max(start, interval.start) <= min(end, interval.end):
                    new_car_segments[segment] = interval

            new_segments[car] = new_car_segments

        return new_segments

    def get_visible_cars(self) -> dict[str, dict[SegmentInterval, Interval]]:
        """
        Returns the visible cars in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each segment (uid) to the interval of that segment
        """
        if not self._visible_cars_filtered:
            self._visible_cars = self._compute_visible_cars_in_view(self._visible_cars)
            self._visible_cars_filtered = True
        return self._visible_cars

    def get_reserved_segments(self) -> dict[str, dict[SegmentInterval, Interval]]:
        """
        Returns the reserved cars in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each reserved segment (uid) to the interval of that segment
        """
        if not self._reserved_segments_filtered:
            self._reserved_segments = self._compute_reserved_segments_in_view(self._reserved_segments)
            self._reserved_segments_filtered = True
        return self._reserved_segments

    def get_claimed_segments(self) -> dict[str, dict[SegmentInterval, Interval]]:
        """
        Returns the claimed segments in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each claimed segment (uid) to the interval of that segment
        """
        if not self._claimed_segments_filtered:
            self._claimed_segments = self._compute_claimed_segments_in_view(self._claimed_segments)
            self._claimed_segments_filtered = True
        return self._claimed_segments
