import math

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.road_network.road_network import Goal


def reached_goal(car: Car, reservation_management: ReservationManagement) -> bool:
    """
    Check if a car has reached its goal.

    Args:
        car (Car): The car to check.
        goal (Goal): The goal to check against.

    Returns:
        bool: True if the car has reached the goal, False otherwise.
    """
    
    if reservation_management.get_car_reservation(car.id, 0).segment == car.goal.lane_segment:
        if math.dist(car.get_center(reservation_management), [car.goal.pos.x, car.goal.pos.y]) < car.size // 3:
            return True
    return False


    
def collision_check(car1: Car, car2: Car, reservation_management: ReservationManagement) -> bool:
    """
    Check whether two cars' bodies overlap on a shared segment.

    Each car's body is the half-open interval [lo, hi) its size occupies on
    every segment it straddles, in that segment's own coordinates. Two bodies
    collide iff those intervals overlap on some shared segment; bumper to
    bumper (hi1 == lo2) is not a collision.

    Args:
        car1 (Car): One car.
        car2 (Car): The other car.
        reservation_management (ReservationManagement): The reservation book
            both cars' footprints are read from.

    Returns:
        bool: True if there is a collision, False otherwise.
    """
    car1_segments = car1.get_size_segments(reservation_management)
    car2_segments = car2.get_size_segments(reservation_management)
    for segment_car1 in car1_segments:
        segment_car2 = next((seg for seg in car2_segments if segment_car1.segment == seg.segment), None)
        if segment_car2 is None:
            continue

        # A footprint runs from `begin` towards `end` along the lane's
        # direction of travel, so on a reverse lane both are negative and
        # |end| > |begin|. Ordering the pair rather than assuming which is
        # which keeps the test direction-agnostic.
        lo1, hi1 = sorted((abs(segment_car1.begin), abs(segment_car1.end)))
        lo2, hi2 = sorted((abs(segment_car2.begin), abs(segment_car2.end)))

        # Plain interval overlap. The four strict three-way comparisons this
        # replaces missed the case of two exactly coincident footprints --
        # total overlap, the worst collision there is, reported as none.
        if lo1 < hi2 and lo2 < hi1:
            return True

    return False