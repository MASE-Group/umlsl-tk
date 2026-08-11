from typing import TYPE_CHECKING, TypeVar, Generic, Callable

from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
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

    def __init__(self, virtual_lanes: list[VirtualLane], segments_in_view: list[Segment],
                 horizon: Interval, ego: 'Car',
                 visible_cars: dict[str, dict[Segment, Interval]],
                 reserved_segments: dict[str, dict[Segment, Interval]],
                 claimed_segments: dict[str, dict[Segment, Interval]],
                 ):
        self.virtual_lanes = virtual_lanes
        self.segments_in_view = segments_in_view
        self.horizon = horizon
        self.ego = ego

        self._lazy_visible_cars = LazyEvaluator(
            visible_cars,
            lambda old_cars: self._compute_visible_cars_in_view(old_cars)
        )
        self._lazy_reserved_segments = LazyEvaluator(
            reserved_segments,
            lambda old_reserved: self._compute_reserved_segments_in_view(old_reserved)
        )
        self._lazy_claimed_segments = LazyEvaluator(
            claimed_segments,
            lambda old_claimed: self._compute_claimed_segments_in_view(old_claimed)
        )

    def chop_horizontally(self, split: float) -> tuple['View', 'View']:
        """
        Chops the View horizontally at the given split value. That means the horizon is split into two parts (at the
        given value) and the two parts are returned as two separate Views.

        Returns:
            left, right: where left is the left View and right is the right View
        """
        left_horizon = Interval(self.horizon.start, split)
        left_view = self._construct_view(left_horizon, self.virtual_lanes)

        right_horizon = Interval(split, self.horizon.end)
        right_view = self._construct_view(right_horizon, self.virtual_lanes)

        return left_view, right_view

    def chop_vertically(self, split: int) -> tuple['View', 'View']:
        """
        Chops the View vertically at the given split index. That means the virtual lanes are split into two parts (the
        lower and upper part) and the two parts are returned as two separate Views.

        Returns:
            lower, upper: where lower is the lower View and upper is the upper View
        """
        lower_lanes = self.virtual_lanes[:split]  # take all lanes whose index is < split_index
        lower_view = self._construct_view(self.horizon, lower_lanes)

        upper_lanes = self.virtual_lanes[split:]
        upper_view = self._construct_view(self.horizon, upper_lanes)

        return lower_view, upper_view

    def _construct_view(self, horizon: Interval, lanes: list[VirtualLane]) -> 'View':
        segments_in_view: list[Segment] = []
        new_virtual_lanes: list[VirtualLane] = []

        for virtual_lane in lanes:
            new_virtual_lane = []

            for segment_interval in virtual_lane.segment_intervals:
                # only take those segments that are in the horizon
                if horizon.intersects(segment_interval.interval):
                    segments_in_view.append(segment_interval.segment)
                    new_virtual_lane.append(segment_interval)

            if len(new_virtual_lane) > 0:
                new_virtual_lanes.append(VirtualLane(new_virtual_lane))

        return View(
            new_virtual_lanes,
            segments_in_view,
            horizon,
            self.ego,
            self._lazy_visible_cars.data,
            self._lazy_reserved_segments.data,
            self._lazy_claimed_segments.data
        )

    def _compute_visible_cars_in_view(self, old_cars: dict[str, dict[Segment, Interval]]):
        # only consider cars that intersect with the horizon
        updated_visible_cars: dict[str, dict[Segment, Interval]] = dict()
        for intersecting_car, occupied_segment_interval in old_cars.items():
            # if there is any intersection with the horizon, we can put all the occupied segments of the car in the view
            # this won't break the logic and safes us computation time
            any_intersects = any(
                occupied_segment in self.segments_in_view and occupied_interval.intersects(self.horizon)
                for occupied_segment, occupied_interval in occupied_segment_interval.items()
            )
            if any_intersects:
                updated_visible_cars[intersecting_car] = occupied_segment_interval

        return updated_visible_cars

    def _compute_reserved_segments_in_view(self, old_reserved_segments: dict[str, dict[Segment, Interval]]):
        return self._recompute_segments_in_view(old_reserved_segments)

    def _compute_claimed_segments_in_view(self, old_claimed_segments: dict[str, dict[Segment, Interval]]):
        return self._recompute_segments_in_view(old_claimed_segments)

    def _recompute_segments_in_view(self, old_segments: dict[str, dict[Segment, Interval]]):
        new_segments: dict[str, dict[Segment, Interval]] = dict()
        for car, reserved_segments in old_segments.items():
            new_car_segments: dict[Segment, Interval] = dict()
            for segment, interval in reserved_segments.items():
                if segment in self.segments_in_view and self.horizon.intersects(interval):
                    new_car_segments[segment] = interval

            new_segments[car] = new_car_segments

        return new_segments

    def get_visible_cars(self) -> dict[str, dict[Segment, Interval]]:
        """
        Returns the visible cars in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each segment (uid) to the interval of that segment
        """
        return self._lazy_visible_cars.acquire_data()

    def get_reserved_segments(self) -> dict[str, dict[Segment, Interval]]:
        """
        Returns the reserved cars in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each reserved segment (uid) to the interval of that segment
        """
        return self._lazy_reserved_segments.acquire_data()

    def get_claimed_segments(self) -> dict[str, dict[Segment, Interval]]:
        """
        Returns the claimed segments in the view.

        Returns:
            the a map that maps each car (uid) to a map that maps each claimed segment (uid) to the interval of that segment
        """
        return self._lazy_claimed_segments.acquire_data()
