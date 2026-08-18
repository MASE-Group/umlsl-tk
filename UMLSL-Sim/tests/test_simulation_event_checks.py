"""Unit tests for `simulation.event_checks` -- goal arrival and collision.

These two predicates are what `TrafficEnv._execute_action` scores a tick by, so
a false negative in `collision_check` is a crash the simulation never notices.
"""

import unittest

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.event_checks import collision_check, reached_goal
from umlsl_sim.simulation.road_network.road_network import Goal, SegmentInfo

from tests.helpers import TEST_COLOR, place_car, single_crossing_world, two_lane_world


class TestReachedGoal(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_a_car_on_top_of_its_goal_has_reached_it(self):
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40,
                        goal_segment=self.segment)
        car.goal = Goal(self.segment, TEST_COLOR, loc=car.loc + car.size // 2)
        car.update_position(self.rm)
        self.assertTrue(reached_goal(car, self.rm))

    def test_a_car_on_the_right_segment_but_far_from_the_goal_has_not(self):
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40,
                        goal_segment=self.segment)
        car.goal = Goal(self.segment, TEST_COLOR, loc=180)
        self.assertFalse(reached_goal(car, self.rm))

    def test_a_car_on_a_different_segment_has_not_reached_its_goal(self):
        other = self.world.lane_segment("v1", "right")
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40,
                        goal_segment=other)
        self.assertFalse(reached_goal(car, self.rm))

    def test_the_tolerance_scales_with_the_cars_size(self):
        """Arrival is `dist(centre, goal) < size // 3`, so a longer car has a
        wider catchment -- an intentional consequence worth pinning."""
        small = place_car(self.world, self.segment, loc=0, speed=0, size=30,
                          goal_segment=self.segment, name="Small")
        big = place_car(self.world, self.world.lane_segment("v1", "right"),
                        loc=0, speed=0, size=90, goal_segment=self.segment,
                        name="Big")
        centre = small.get_center(self.rm)
        offset_goal = Goal(self.segment, TEST_COLOR)
        offset_goal.pos.x, offset_goal.pos.y = centre[0] + 20, centre[1]
        small.goal = offset_goal
        self.assertFalse(reached_goal(small, self.rm))

        big_centre = big.get_center(self.rm)
        big.goal = Goal(self.segment, TEST_COLOR)
        big.goal.pos.x, big.goal.pos.y = big_centre[0], big_centre[1]
        self.assertFalse(reached_goal(big, self.rm),
                         "big is not on the goal's segment")

    def test_arrival_is_measured_from_the_cars_centre(self):
        car = place_car(self.world, self.segment, loc=60, speed=0, size=40,
                        goal_segment=self.segment)
        centre = car.get_center(self.rm)
        car.goal = Goal(self.segment, TEST_COLOR)
        car.goal.pos.x, car.goal.pos.y = centre[0], centre[1]
        self.assertTrue(reached_goal(car, self.rm))


class TestCollisionCheck(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_two_cars_far_apart_do_not_collide(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        second = place_car(self.world, self.segment, loc=150, speed=0, size=40,
                           name="Other")
        self.assertFalse(collision_check(first, second, self.rm))

    def test_overlapping_bodies_collide(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        second = place_car(self.world, self.segment, loc=20, speed=0, size=40,
                           name="Other")
        self.assertTrue(collision_check(first, second, self.rm))

    def test_the_check_is_symmetric(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        second = place_car(self.world, self.segment, loc=20, speed=0, size=40,
                           name="Other")
        self.assertEqual(collision_check(first, second, self.rm),
                         collision_check(second, first, self.rm))

    def test_bumper_to_bumper_is_not_a_collision(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        second = place_car(self.world, self.segment, loc=40, speed=0, size=40,
                           name="Other")
        self.assertFalse(collision_check(first, second, self.rm))

    def test_one_body_inside_another_collides(self):
        big = place_car(self.world, self.segment, loc=0, speed=0, size=100)
        small = place_car(self.world, self.segment, loc=30, speed=0, size=20,
                          name="Small")
        self.assertTrue(collision_check(big, small, self.rm))

    def test_two_exactly_coincident_bodies_collide(self):
        """FIXED (FINDINGS #4): total overlap used to be reported as no collision.

        The old rule was four strict three-way comparisons -- `b2 < b1 < e2`
        and so on -- every one of which is false when the two intervals are
        identical, so the worst possible crash was the one case it missed.
        """
        first = place_car(self.world, self.segment, loc=50, speed=0, size=40)
        second = place_car(self.world, self.segment, loc=50, speed=0, size=40,
                           name="Twin")
        self.assertTrue(collision_check(first, second, self.rm))

    def test_bodies_sharing_a_leading_edge_collide(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=100)
        second = place_car(self.world, self.segment, loc=0, speed=0, size=40,
                           name="Short")
        self.assertTrue(collision_check(first, second, self.rm))

    def test_bodies_sharing_a_trailing_edge_collide(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=100)
        second = place_car(self.world, self.segment, loc=60, speed=0, size=40,
                           name="Short")
        self.assertTrue(collision_check(first, second, self.rm))

    def test_cars_on_different_segments_never_collide(self):
        first = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        second = place_car(self.world, self.world.lane_segment("v1", "right"),
                           loc=0, speed=0, size=40, name="Other")
        self.assertFalse(collision_check(first, second, self.rm))

    def test_cars_in_parallel_lanes_never_collide(self):
        world = two_lane_world()
        rm = world.reservation_management
        first = place_car(world, world.lane_segment("h1", "right", num=0),
                          loc=50, speed=0, size=40)
        second = place_car(world, world.lane_segment("h1", "right", num=1),
                           loc=50, speed=0, size=40, name="Beside")
        self.assertFalse(collision_check(first, second, rm))

    def test_a_reverse_lane_pair_is_judged_the_same_way(self):
        reverse = self.world.lane_segment("h1", "left")
        first = place_car(self.world, reverse, loc=50, speed=0, size=40)
        overlapping = place_car(self.world, reverse, loc=70, speed=0, size=40,
                                name="Other")
        clear = place_car(self.world, reverse, loc=150, speed=0, size=40,
                          name="Clear")
        self.assertTrue(collision_check(first, overlapping, self.rm))
        self.assertFalse(collision_check(first, clear, self.rm))

    def test_a_car_never_collides_with_itself(self):
        """A car compared against itself has identical footprints, which the
        fixed overlap rule *does* report -- so `TrafficEnv` must keep excluding
        the car from its own crash scan, as it does."""
        car = place_car(self.world, self.segment, loc=50, speed=0, size=40)
        self.assertTrue(collision_check(car, car, self.rm),
                        "self-comparison is a total overlap; callers must skip it")

    def test_straddling_cars_are_compared_on_the_segment_they_share(self):
        first = place_car(self.world, self.segment, speed=10, size=40,
                          goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(15):
            first.move(self.rm)
        footprint = first.get_size_segments(self.rm)
        shared = footprint[-1].segment
        other = place_car(self.world, self.world.lane_segment("v1", "left"),
                          loc=0, speed=0, size=40, name="Other")
        self.rm.pop_car_reservation(other.id, 0)
        self.rm.add_car_reservation(
            other.id, SegmentInfo(shared, footprint[-1].begin,
                                  footprint[-1].end, footprint[-1].direction))
        other.loc = footprint[-1].begin
        self.assertTrue(collision_check(first, other, self.rm))


if __name__ == "__main__":
    unittest.main()
