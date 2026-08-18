"""Unit tests for `simulation.safety_checks` -- the collision-freedom rules.

The module's stated invariant is that a car's reservation always covers its
worst-case stopping envelope, so a follower is safe exactly while its projected
end stays behind every leader's worst-case *next* rear. These tests exercise
that boundary from both sides, because a rule that is merely conservative is
useless (nothing may ever move) and a rule that is merely permissive is unsafe.
"""

import unittest

from umlsl_sim.config.logic_constants import MAX_ACC, MAX_DEC
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.reservations.lane_change_claim import LaneChangeClaim
from umlsl_sim.simulation.road_network.road_network import Direction, SegmentInfo
from umlsl_sim.simulation.safety_checks import (
    _other_rear_in_segment,
    lane_change_blocked,
    max_end_growth,
    min_next_rear_advance,
    rear_end_violation,
)

from tests.helpers import place_car, single_crossing_world, two_lane_world


class TestMinNextRearAdvance(unittest.TestCase):
    """The least a live car can move next tick -- it may always brake fully."""

    def test_a_car_that_can_stop_dead_may_advance_nothing(self):
        self.assertEqual(min_next_rear_advance(MAX_DEC), 0)
        self.assertEqual(min_next_rear_advance(0), 0)

    def test_a_car_too_fast_to_stop_must_still_advance(self):
        self.assertEqual(min_next_rear_advance(MAX_DEC + 7), 7)

    def test_it_is_never_negative(self):
        for speed in range(0, 3 * MAX_DEC):
            self.assertGreaterEqual(min_next_rear_advance(speed), 0)

    def test_it_never_exceeds_the_current_speed(self):
        for speed in range(0, 3 * MAX_DEC):
            self.assertLessEqual(min_next_rear_advance(speed), speed)

    def test_it_is_monotone_in_speed(self):
        values = [min_next_rear_advance(v) for v in range(0, 40)]
        self.assertEqual(values, sorted(values))


class TestMaxEndGrowth(unittest.TestCase):
    """The most a car's reservation end can advance -- it may accelerate fully."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()

    def _car(self, speed, max_speed=20, size=40):
        return place_car(self.world, self.world.lane_segment("h1", "right"),
                         speed=speed, max_speed=max_speed, size=size)

    def test_a_wreck_never_grows(self):
        car = self._car(speed=15)
        car.handle_car_death(self.world.reservation_management)
        self.assertEqual(max_end_growth(car), 0)

    def test_growth_is_the_difference_between_the_two_braking_envelopes(self):
        car = self._car(speed=0, max_speed=20)
        faster = min(car.speed + MAX_ACC, car.max_speed)
        self.assertEqual(
            max_end_growth(car),
            faster + car.get_braking_distance(faster) - car.get_braking_distance(car.speed))

    def test_a_car_already_at_its_maximum_still_advances_by_that_maximum(self):
        car = self._car(speed=20, max_speed=20)
        self.assertEqual(max_end_growth(car), car.max_speed)

    def test_body_and_buffer_cancel_out_of_the_difference(self):
        small = self._car(speed=5, size=40)
        big = place_car(self.world, self.world.lane_segment("v1", "right"),
                        speed=5, size=90, name="Big")
        self.assertEqual(max_end_growth(small), max_end_growth(big))

    def test_growth_is_always_positive_for_a_live_car(self):
        for speed in range(0, 21):
            world = single_crossing_world()
            car = place_car(world, world.lane_segment("h1", "right"),
                            speed=speed, max_speed=20)
            self.assertGreater(max_end_growth(car), 0)


class TestOtherRearInSegment(unittest.TestCase):
    """Expressing another car's rear in the coordinates of one shared segment."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_a_car_anchored_on_the_segment_reports_its_own_offset(self):
        car = place_car(self.world, self.segment, loc=70, speed=5)
        reservations = self.rm.get_car_reservations(car.id)
        self.assertEqual(
            _other_rear_in_segment(self.segment, car.id, reservations, False), 70)

    def test_a_car_changing_into_the_segment_maps_its_source_offset_across(self):
        world = two_lane_world()
        source = world.lane_segment("h1", "right", num=0)
        target = world.lane_segment("h1", "right", num=1)
        car = place_car(world, source, loc=70, speed=5)
        reservations = world.reservation_management.get_car_reservations(car.id)
        self.assertEqual(
            _other_rear_in_segment(target, car.id, reservations, True), 70)

    def test_a_car_not_touching_the_segment_reports_nothing(self):
        car = place_car(self.world, self.segment, loc=0, speed=5)
        reservations = self.rm.get_car_reservations(car.id)
        elsewhere = self.world.lane_segment("v1", "right")
        self.assertIsNone(
            _other_rear_in_segment(elsewhere, car.id, reservations, False))

    def test_a_car_straddling_in_reports_a_negative_rear(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(14):
            car.move(self.rm)
        reservations = self.rm.get_car_reservations(car.id)
        if len(reservations) < 2:
            self.skipTest("the car never extended past its own segment")
        ahead = reservations[-1].segment
        rear = _other_rear_in_segment(ahead, car.id, reservations, False)
        self.assertIsNotNone(rear)
        self.assertLess(rear, 0, "its rear has not entered the segment ahead yet")

    def test_a_reverse_lane_rear_is_reported_unsigned(self):
        reverse = self.world.lane_segment("h1", "left")
        car = place_car(self.world, reverse, loc=70, speed=5)
        reservations = self.rm.get_car_reservations(car.id)
        self.assertEqual(
            _other_rear_in_segment(reverse, car.id, reservations, False), 70)


class TestRearEndViolation(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def _projected(self, car, end_offset):
        return [SegmentInfo(self.segment, car.loc,
                            car.loc + end_offset, car.direction)]

    def test_an_empty_road_is_never_a_violation(self):
        car = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        self.assertFalse(rear_end_violation(car, self._projected(car, 70), self.rm,
                                            {car.id: car}))

    def test_a_car_alone_does_not_collide_with_itself(self):
        car = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        self.assertFalse(rear_end_violation(car, self._projected(car, 190), self.rm,
                                            {car.id: car}))

    def test_reaching_past_a_stopped_leader_is_a_violation(self):
        follower = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        leader = place_car(self.world, self.segment, loc=100, speed=0, size=40,
                           name="Leader")
        cars = {follower.id: follower, leader.id: leader}
        self.assertTrue(
            rear_end_violation(follower, self._projected(follower, 150), self.rm, cars))

    def test_stopping_short_of_a_leader_is_safe(self):
        follower = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        leader = place_car(self.world, self.segment, loc=100, speed=0, size=40,
                           name="Leader")
        cars = {follower.id: follower, leader.id: leader}
        self.assertFalse(
            rear_end_violation(follower, self._projected(follower, 90), self.rm, cars))

    def test_a_moving_leader_grants_the_room_it_must_vacate(self):
        follower = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        fast = place_car(self.world, self.segment, loc=100,
                         speed=MAX_DEC + 10, size=40, max_speed=20, name="Fast")
        cars = {follower.id: follower, fast.id: fast}
        # The leader must advance at least min_next_rear_advance == 10.
        self.assertFalse(
            rear_end_violation(follower, self._projected(follower, 110), self.rm, cars))
        self.assertTrue(
            rear_end_violation(follower, self._projected(follower, 111), self.rm, cars))

    def test_a_car_behind_is_not_our_problem(self):
        car = place_car(self.world, self.segment, loc=100, speed=10, size=40)
        behind = place_car(self.world, self.segment, loc=0, speed=20, size=40,
                           name="Behind")
        cars = {car.id: car, behind.id: behind}
        self.assertFalse(
            rear_end_violation(car, self._projected(car, 70), self.rm, cars))

    def test_a_car_at_exactly_our_rear_counts_as_a_leader(self):
        car = place_car(self.world, self.segment, loc=50, speed=10, size=40)
        tie = place_car(self.world, self.segment, loc=50, speed=0, size=40, name="Tie")
        cars = {car.id: car, tie.id: tie}
        self.assertTrue(
            rear_end_violation(car, self._projected(car, 60), self.rm, cars))

    def test_a_car_the_lookup_does_not_know_is_skipped(self):
        follower = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        place_car(self.world, self.segment, loc=100, speed=0, size=40, name="Ghost")
        self.assertFalse(
            rear_end_violation(follower, self._projected(follower, 150), self.rm,
                               {follower.id: follower}))

    def test_a_car_committed_to_changing_into_our_lane_is_seen(self):
        world = two_lane_world()
        rm = world.reservation_management
        target = world.lane_segment("h1", "right", num=0)
        source = world.lane_segment("h1", "right", num=1)
        follower = place_car(world, target, loc=0, speed=10, size=40)
        merger = place_car(world, source, loc=100, speed=0, size=40, name="Merger")
        rm.set_lane_change_claim(merger.id, LaneChangeClaim(target, 0))
        projected = [SegmentInfo(target, follower.loc, follower.loc + 150,
                                 follower.direction)]
        self.assertTrue(rear_end_violation(follower, projected, rm,
                                           {follower.id: follower, merger.id: merger}))

    def test_crossings_in_the_projection_are_governed_elsewhere(self):
        """Only lane segments are checked here; crossings are handled by the
        time-to-leave and priority rules in the controllers."""
        car = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        crossing = self.segment.end_crossing
        blocker = place_car(self.world, self.world.lane_segment("v1", "right"),
                            speed=0, name="Blocker")
        self.rm.add_car_reservation(
            blocker.id, SegmentInfo(crossing, 0, 40, Direction.DOWN))
        projected = [SegmentInfo(self.segment, 0, 200, car.direction),
                     SegmentInfo(crossing, 0, 40, Direction.DOWN)]
        self.assertFalse(rear_end_violation(car, projected, self.rm,
                                            {car.id: car, blocker.id: blocker}))


class TestLaneChangeBlocked(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.source = self.world.lane_segment("h1", "right", num=0)
        self.target = self.world.lane_segment("h1", "right", num=1)

    def test_an_empty_target_lane_is_open(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        self.assertFalse(lane_change_blocked(car, self.target, 0, 70, self.rm, [car]))

    def test_a_stopped_car_just_ahead_in_the_target_lane_blocks(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        other = place_car(self.world, self.target, loc=50, speed=0, size=40,
                          name="Ahead")
        self.assertTrue(
            lane_change_blocked(car, self.target, 0, 100, self.rm, [car, other]))

    def test_a_car_far_enough_ahead_does_not_block(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        other = place_car(self.world, self.target, loc=150, speed=0, size=40,
                          name="Ahead")
        self.assertFalse(
            lane_change_blocked(car, self.target, 0, 100, self.rm, [car, other]))

    def test_a_car_at_exactly_our_rear_blocks(self):
        car = place_car(self.world, self.source, loc=50, speed=10, size=40)
        other = place_car(self.world, self.target, loc=50, speed=0, size=40,
                          name="Tie")
        self.assertTrue(
            lane_change_blocked(car, self.target, 50, 120, self.rm, [car, other]))

    def test_a_car_close_behind_in_the_target_lane_blocks(self):
        """Cars behind matter here and not in `rear_end_violation`: they cannot
        see us until our registration lands, so we must leave them room."""
        car = place_car(self.world, self.source, loc=100, speed=5, size=40)
        behind = place_car(self.world, self.target, loc=0, speed=20, size=40,
                           max_speed=20, name="Behind")
        self.assertTrue(
            lane_change_blocked(car, self.target, 100, 170, self.rm, [car, behind]))

    def test_a_car_far_enough_behind_does_not_block(self):
        car = place_car(self.world, self.source, loc=180, speed=5, size=40)
        behind = place_car(self.world, self.target, loc=0, speed=0, size=40,
                           max_speed=20, name="Behind")
        self.assertFalse(
            lane_change_blocked(car, self.target, 180, 195, self.rm, [car, behind]))

    def test_a_car_behind_whose_reservation_runs_through_the_segment_blocks(self):
        car = place_car(self.world, self.source, loc=180, speed=5, size=40)
        behind = place_car(self.world, self.target, loc=0, speed=20, size=40,
                           max_speed=20, name="Behind",
                           goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(8):
            behind.move(self.rm)
        if len(self.rm.get_car_reservations(behind.id)) < 2:
            self.skipTest("the follower never extended past the segment")
        self.assertTrue(
            lane_change_blocked(car, self.target, 195, 199, self.rm, [car, behind]))

    def test_we_never_block_ourselves(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        self.rm.set_lane_change_claim(car.id, LaneChangeClaim(self.target, 0))
        self.assertFalse(lane_change_blocked(car, self.target, 0, 70, self.rm, [car]))

    def test_another_car_already_committed_to_the_same_gap_blocks(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        third = self.world.lane_segment("h1", "left", num=0)
        rival = place_car(self.world, third, loc=50, speed=0, size=40, name="Rival")
        self.rm.set_lane_change_claim(rival.id, LaneChangeClaim(self.target, 0))
        self.assertTrue(
            lane_change_blocked(car, self.target, 0, 100, self.rm, [car, rival]))

    def test_a_car_the_list_does_not_contain_is_skipped(self):
        car = place_car(self.world, self.source, loc=0, speed=10, size=40)
        place_car(self.world, self.target, loc=50, speed=0, size=40, name="Ghost")
        self.assertFalse(lane_change_blocked(car, self.target, 0, 100, self.rm, [car]))


class TestSafetyRuleIsInductive(unittest.TestCase):
    """The module's core claim: any accepted state has a safe successor.

    Braking keeps a follower's reservation end where it is, while a leader's
    rear never moves backwards -- so if full braking is safe now it stays safe.
    """

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_full_braking_stays_safe_as_a_leader_moves_on(self):
        follower = place_car(self.world, self.segment, loc=0, speed=10, size=40)
        leader = place_car(self.world, self.segment, loc=120, speed=10, size=40,
                           name="Leader")
        cars = {follower.id: follower, leader.id: leader}
        braked = [SegmentInfo(self.segment, follower.loc,
                              follower.loc + follower.get_braking_distance(0),
                              follower.direction)]
        self.assertFalse(rear_end_violation(follower, braked, self.rm, cars))

        leader.loc += leader.speed
        self.rm.update_car_reservation_begin(leader.id, 0, leader.loc)
        self.assertFalse(rear_end_violation(follower, braked, self.rm, cars),
                         "a leader moving away can never make us unsafe")


if __name__ == "__main__":
    unittest.main()
