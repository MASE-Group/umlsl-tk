

import random
from typing import List, Tuple

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.config.logic_constants import BLOCK_SIZE, CROSSING_MAX_SPEED, LANE_MAX_SPEED, MINIMAL_SPEED
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.road_network.road_network import Color, Goal, LaneSegment, Road, direction_sign, true_direction
from umlsl_sim.palettes.color_names import colors
from umlsl_sim.palettes.car_colors import selected_colors
from umlsl_sim.factories.car_spec import CarSpec, resolve_position


def _footprint(segment_begin: int, loc: int, size: int, direction) -> Tuple[int, int]:
    """Axis interval [lo, hi] a car body occupies on its lane segment, matching
    ``Car.update_position``: the reference point is ``segment_begin + loc`` and
    the body extends ``size`` opposite the travel direction."""
    ref = segment_begin + loc
    if true_direction[direction]:
        return ref, ref + size
    return ref - size, ref


def total_lane_segments(roads: List[Road]) -> int:
    return sum(
        1
        for road in roads
        for lane in road.right_lanes + road.left_lanes
        for ls in lane.segments
        if isinstance(ls, LaneSegment)
    )


def _free_lane_segments(roads: List[Road],
                        cars: List['Car'],
                        reservation_management: ReservationManagement) -> List[LaneSegment]:
    """Lane segments no existing car is anchored on (a car's reservation 0)."""
    occupied = {
        id(reservation_management.get_car_reservation(car.id, 0).segment)
        for car in cars
    }
    return [
        ls
        for road in roads
        for lane in road.right_lanes + road.left_lanes
        for ls in lane.segments
        if isinstance(ls, LaneSegment) and id(ls) not in occupied
    ]


def _pick_name_color(cars: List['Car']) -> Tuple[str, Color]:
    for c in selected_colors:
        if not any(car.name == c for car in cars):
            return c, selected_colors[c]
    for c in colors:
        if not any(car.name == c for car in cars):
            return c, colors[c]
    return "", (0, 0, 0)

def create_random_car(roads: List[Road], cars: List['Car'], car_type: CarType, reservation_management: ReservationManagement) -> 'Car':
    """
    Create a random car that does not overlap with existing cars.
    Randomly selects a color, lane segment, speed, size. The location is set to 0.

    Args:
        segments (List[Segment]): The list of segments to place the car in.
        cars (List[Car]): The list of existing cars.

    Returns:
        Car: The randomly created car.
    """
    name, color = _pick_name_color(cars)

    empty_lane_segments = _free_lane_segments(roads, cars, reservation_management)
    if not empty_lane_segments:
        raise ValueError(
            f"Cannot place car #{len(cars) + 1}: every lane segment in this road "
            f"network is already occupied. The network has "
            f"{total_lane_segments(roads)} lane segments, which is the hard "
            f"upper bound on the number of cars; lower `players` in the scenario."
        )

    lane_segment = random.choice(empty_lane_segments)

    first_goal = create_goal(color, lane_segment, roads)
    second_goal = create_goal(color, lane_segment, roads, first_goal)

    if len(cars) % 2 == 0:
        max_speed = random.randint(CROSSING_MAX_SPEED, LANE_MAX_SPEED)
    else:
        max_speed = random.randint(MINIMAL_SPEED, CROSSING_MAX_SPEED)
    speed = random.randint(1, max_speed)

    size = random.randint(BLOCK_SIZE // 2, 3 * BLOCK_SIZE // 2)
    loc = 0

    return Car(name=name,
               type=car_type,
               loc=loc,
               segment=lane_segment,
               speed=speed,
               size=size,
               color=color,
               max_speed=max_speed,
               first_goal=first_goal,
               second_goal=second_goal,
               reservation_management=reservation_management)


def create_predefined_car(spec: CarSpec,
                          roads: List[Road],
                          cars: List['Car'],
                          reservation_management: ReservationManagement) -> 'Car':
    """
    Create a car from a predefined spec, falling back to the random logic
    used by `create_random_car` for any field left as None on the spec.
    """
    if spec.start is not None:
        lane_segment, loc = resolve_position(roads, spec.start)
        # resolve_position returns an unsigned offset from segment.begin, but a
        # car's loc is signed by travel direction (negative on LEFT/DOWN lanes),
        # the same convention Car.move() accumulates and Goal applies. Without
        # this sign, reverse-lane predefined starts are mirrored to
        # (2*begin - position) and land off the lane.
        loc = direction_sign[lane_segment.lane.direction] * loc
        # Occupancy check. When the spec carries an explicit size (as saved
        # scenarios do), reject only a genuine footprint overlap on the same
        # segment — several cars legitimately share one long lane segment at
        # different positions in a live frame. When size is unknown, keep the
        # coarse segment-level exclusion (car is spawned at loc 0).
        if spec.size is not None:
            new_lo, new_hi = _footprint(lane_segment.begin, loc, spec.size,
                                        lane_segment.lane.direction)
            for other in cars:
                other_seg = reservation_management.get_car_reservation(other.id, 0).segment
                if other_seg is not lane_segment:
                    continue
                o_lo, o_hi = _footprint(lane_segment.begin, other.loc, other.size, other.direction)
                if new_lo < o_hi and o_lo < new_hi:
                    raise ValueError(
                        f"Predefined start {spec.start} overlaps existing car {other.name!r}"
                    )
        elif any(
            lane_segment == reservation_management.get_car_reservation(car.id, 0).segment
            for car in cars
        ):
            raise ValueError(
                f"Predefined start segment {spec.start} is already occupied by another car"
            )
    else:
        empty_lane_segments = _free_lane_segments(roads, cars, reservation_management)
        if not empty_lane_segments:
            raise ValueError(
                f"Cannot place predefined car {spec.name or '<unnamed>'!r}: every "
                f"lane segment in this road network is already occupied. Give the "
                f"car an explicit `start`, or lower `players` in the scenario."
            )
        lane_segment = random.choice(empty_lane_segments)
        loc = 0

    if spec.name is not None and spec.color is not None:
        name, color = spec.name, spec.color
    else:
        auto_name, auto_color = _pick_name_color(cars)
        name = spec.name if spec.name is not None else auto_name
        color = spec.color if spec.color is not None else auto_color

    if spec.first_goal is not None:
        first_goal_seg, first_goal_loc = resolve_position(roads, spec.first_goal)
        first_goal = Goal(first_goal_seg, color, loc=first_goal_loc)
    else:
        first_goal = create_goal(color, lane_segment, roads)

    if spec.second_goal is not None:
        second_goal_seg, second_goal_loc = resolve_position(roads, spec.second_goal)
        second_goal = Goal(second_goal_seg, color, loc=second_goal_loc)
    else:
        second_goal = create_goal(color, lane_segment, roads, first_goal)

    if spec.max_speed is not None:
        max_speed = spec.max_speed
    elif len(cars) % 2 == 0:
        max_speed = random.randint(CROSSING_MAX_SPEED, LANE_MAX_SPEED)
    else:
        max_speed = random.randint(MINIMAL_SPEED, CROSSING_MAX_SPEED)

    speed = spec.speed if spec.speed is not None else random.randint(1, max_speed)
    size = spec.size if spec.size is not None else random.randint(BLOCK_SIZE // 2, 3 * BLOCK_SIZE // 2)

    return Car(name=name,
               type=spec.type,
               loc=loc,
               segment=lane_segment,
               speed=speed,
               size=size,
               color=color,
               max_speed=max_speed,
               first_goal=first_goal,
               second_goal=second_goal,
               reservation_management=reservation_management)


def create_goal(color: Color, car_segment:LaneSegment, roads: List[Road], first_goal: Goal | None = None) -> Goal:
    """
    Place a goal for the specified car.

    Args:
        car (Car): The car.
    """

    empty_lane_segments = [
        ls
        for road in roads
        for lane in road.right_lanes + road.left_lanes
        for ls in lane.segments
        if isinstance(ls, LaneSegment) and \
            not (road == car_segment.lane.road and lane.direction == car_segment.lane.direction and ls.num == car_segment.num) and \
            (first_goal is None or not (road == first_goal.lane_segment.lane.road and lane.direction == first_goal.lane_segment.lane.direction and ls.num == first_goal.lane_segment.num))
    ]
    if not empty_lane_segments:
        raise ValueError(
            "Cannot place a goal: no lane segment remains once the car's own "
            "segment (and its first goal, if any) are excluded. The road network "
            "is too small — add a road or a lane."
        )
    lane_segment = random.choice(empty_lane_segments)
    return Goal(lane_segment, color)