"""Small deterministic worlds, shared by the whole suite.

Every builder returns a freshly constructed road network -- `Road` objects own
their lanes and `create_segments` fills in the segment graph, so nothing here is
shared between tests and no test can leak geometry into another.

The worlds are deliberately tiny. A bundled scenario has hundreds of segments
and is the right thing to run an *episode* against (see `tests/integration/`),
but it is the wrong thing to assert a single reservation offset against, because
nothing in it is small enough to work out by hand.
"""

from typing import List, Optional, Tuple

from umlsl_sim.config.logic_constants import BLOCK_SIZE
from umlsl_sim.factories.create_segments import create_segments
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    Direction,
    Goal,
    Intersection,
    LaneSegment,
    Road,
    Segment,
)

#: A colour to give test cars that no assertion depends on.
TEST_COLOR: Tuple[int, int, int] = (10, 20, 30)


class World:
    """A built road network, plus the lookups a test needs to navigate it."""

    def __init__(self, roads: List[Road]) -> None:
        self.roads: List[Road] = roads
        self.segments: List[Segment]
        self.intersections: List[Intersection]
        self.segments, self.intersections = create_segments(roads)
        self.reservation_management = ReservationManagement()

    # --- lookups -------------------------------------------------------------

    def road(self, name: str) -> Road:
        return next(r for r in self.roads if r.name == name)

    def lane(self, road_name: str, direction: str, num: int = 0):
        """The `num`-th lane of `road_name` on the "right" or "left" side."""
        road = self.road(road_name)
        lanes = road.right_lanes if direction == "right" else road.left_lanes
        return lanes[num]

    def lane_segment(self, road_name: str, direction: str = "right",
                     num: int = 0, index: int = 0) -> LaneSegment:
        """The `index`-th LaneSegment of a lane, in the order it was built."""
        lane = self.lane(road_name, direction, num)
        lane_segments = [s for s in lane.segments if isinstance(s, LaneSegment)]
        return lane_segments[index]

    def crossing_segments(self, road_name: str, direction: str = "right",
                          num: int = 0) -> List[CrossingSegment]:
        lane = self.lane(road_name, direction, num)
        return [s for s in lane.segments if isinstance(s, CrossingSegment)]

    def lane_segments(self) -> List[LaneSegment]:
        return [s for s in self.segments if isinstance(s, LaneSegment)]


def single_crossing_world() -> World:
    """One horizontal and one vertical road meeting at a single intersection.

    Both roads carry one lane each way, so each of the four lanes owns exactly
    one LaneSegment (200 long) and two CrossingSegments, and the segment graph
    closes into a cycle -- a car can drive round it indefinitely, which is what
    makes it usable for multi-tick tests without anything running off the end.
    """
    return World([Road("h1", True, 200, 1, 1), Road("v1", False, 200, 1, 1)])


def two_lane_world() -> World:
    """As `single_crossing_world`, but the horizontal road has two right lanes.

    The second right lane is what makes a lane change expressible: lane 0 and
    lane 1 of `h1` run alongside each other, share a segment number, and are
    each other's `get_adjacent_lane_segment` result.
    """
    return World([Road("h1", True, 200, 2, 1), Road("v1", False, 200, 1, 1)])


def ring_world() -> World:
    """Four one-way roads forming a closed circuit, as `circuit.json` does.

    Four intersections, four lane segments, and exactly one route round the
    loop -- so a car's A* plan is forced and can be asserted exactly.
    """
    return World([
        Road("hb", True, 0, 1, 0),
        Road("ht", True, 400, 0, 1),
        Road("vl", False, 0, 1, 0),
        Road("vr", False, 400, 0, 1),
    ])


def place_car(world: World,
              segment: LaneSegment,
              loc: int = 0,
              speed: int = 0,
              size: int = BLOCK_SIZE,
              max_speed: int = 20,
              name: str = "test",
              car_type: CarType = CarType.NPC,
              goal_segment: Optional[LaneSegment] = None,
              second_goal_segment: Optional[LaneSegment] = None) -> Car:
    """Build a car on `segment` and register it in `world`'s reservation book.

    `loc` is given unsigned and signed here by the lane's direction of travel,
    the convention `Car.move` accumulates in -- so a test says "60 along the
    segment" and gets that on a reverse lane too.
    """
    from umlsl_sim.simulation.road_network.road_network import direction_sign

    goal_segment = goal_segment if goal_segment is not None else segment
    second_goal_segment = (second_goal_segment if second_goal_segment is not None
                           else goal_segment)
    return Car(
        name=name,
        type=car_type,
        loc=direction_sign[segment.lane.direction] * loc,
        segment=segment,
        speed=speed,
        size=size,
        color=TEST_COLOR,
        max_speed=max_speed,
        first_goal=Goal(goal_segment, TEST_COLOR),
        second_goal=Goal(second_goal_segment, TEST_COLOR),
        reservation_management=world.reservation_management,
    )


def reservation_segments(world: World, car: Car) -> List[Segment]:
    """The segments a car currently holds, in reservation order."""
    return [si.segment for si in world.reservation_management.get_car_reservations(car.id)]


class RecordingController:
    """A `simulation.ports.CarController` that replays a scripted action list.

    Lets a test drive `TrafficEnv` through exact actions instead of whatever
    the A* controller decides, which is the difference between asserting the
    environment's tick and asserting the NPC policy's taste.
    """

    def __init__(self, car: Car, cars: List[Car],
                 reservation_management: ReservationManagement,
                 actions: Optional[List[Tuple[int, int]]] = None) -> None:
        self.car = car
        self.cars = cars
        self.reservation_management = reservation_management
        self.actions: List[Tuple[int, int]] = list(actions or [])
        self.requested: List[Tuple[int, int]] = []

    def get_action(self) -> Tuple[int, int]:
        action = self.actions.pop(0) if self.actions else (0, 0)
        self.requested.append(action)
        return action


def constant_controller_factory(action: Tuple[int, int] = (0, 0)):
    """A `CarControllerFactory` whose controllers always return `action`."""

    def factory(car: Car, cars: List[Car],
                reservation_management: ReservationManagement) -> RecordingController:
        controller = RecordingController(car, cars, reservation_management)
        controller.actions = []
        controller._constant = action

        def get_action(_controller=controller):
            _controller.requested.append(action)
            return action

        controller.get_action = get_action
        return controller

    return factory


__all__ = [
    "TEST_COLOR",
    "World",
    "single_crossing_world",
    "two_lane_world",
    "ring_world",
    "place_car",
    "reservation_segments",
    "RecordingController",
    "constant_controller_factory",
    "Direction",
]
