"""Unit tests for `simulation.car` -- one vehicle's state, route and motion.

`Car` holds no segment of its own: where it is lives in the reservation book,
and the car holds only an offset into whatever it currently reserves. Most of
what follows is therefore a statement about a car *and* a
`ReservationManagement` together.
"""

import itertools
import unittest

from umlsl_sim.config.logic_constants import (
    BLOCK_SIZE,
    BUFFER,
    CLAIM_TIME,
    CROSSING_MAX_SPEED,
    LANECHANGE_TIME_STEPS,
    LANE_MAX_SPEED,
    MAX_DEC,
)
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    Direction,
    Goal,
    LaneSegment,
    Problem,
    SegmentInfo,
)

from tests.helpers import (
    TEST_COLOR,
    place_car,
    reservation_segments,
    ring_world,
    single_crossing_world,
    two_lane_world,
)


class TestCarIdentity(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()

    def test_the_id_combines_the_name_with_a_counter(self):
        car = place_car(self.world, self.world.lane_segment("h1", "right"), name="Blue")
        self.assertEqual(car.id, "Blue_1")

    def test_the_counter_advances_per_car(self):
        first = place_car(self.world, self.world.lane_segment("h1", "right"), name="A")
        second = place_car(self.world, self.world.lane_segment("v1", "right"), name="B")
        self.assertEqual((first.id, second.id), ("A_1", "B_2"))

    def test_ids_stay_distinct_when_names_collide(self):
        first = place_car(self.world, self.world.lane_segment("h1", "right"), name="Same")
        second = place_car(self.world, self.world.lane_segment("v1", "right"), name="Same")
        self.assertNotEqual(first.id, second.id)

    def test_resetting_the_counter_restarts_numbering(self):
        place_car(self.world, self.world.lane_segment("h1", "right"), name="A")
        Car.reset_id_counter()
        world = single_crossing_world()
        car = place_car(world, world.lane_segment("h1", "right"), name="A")
        self.assertEqual(car.id, "A_1")

    def test_the_counter_is_shared_by_the_class(self):
        self.assertIsInstance(Car._id_counter, itertools.count)


class TestCarInitialState(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_the_car_faces_the_way_its_lane_runs(self):
        car = place_car(self.world, self.segment)
        self.assertIs(car.direction, self.segment.lane.direction)

    def test_a_new_car_is_alive_stationary_in_time_and_unscored(self):
        car = place_car(self.world, self.segment)
        self.assertFalse(car.get_death_status())
        self.assertEqual(car.time, 0)
        self.assertEqual(car.score, 0)
        self.assertIsNone(car.changing_lane)
        self.assertFalse(car.illegal_move)

    def test_exactly_one_reservation_is_registered(self):
        car = place_car(self.world, self.segment)
        self.assertEqual(reservation_segments(self.world, car), [self.segment])

    def test_the_reservation_covers_the_braking_envelope(self):
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        info = self.rm.get_car_reservation(car.id, 0)
        self.assertEqual(info.begin, 0)
        self.assertEqual(abs(info.end), car.get_braking_distance())

    def test_the_car_appears_in_the_segments_occupancy(self):
        car = place_car(self.world, self.segment)
        self.assertIn(car.id, self.rm.get_cars_on_segment(self.segment))

    def test_both_goals_are_kept(self):
        goal_seg = self.world.lane_segment("v1", "right")
        car = place_car(self.world, self.segment, goal_segment=goal_seg)
        self.assertIs(car.goal.lane_segment, goal_seg)
        self.assertIsInstance(car.second_goal, Goal)

    def test_a_reverse_lane_car_holds_a_negative_offset(self):
        reverse = self.world.lane_segment("h1", "left")
        car = place_car(self.world, reverse, loc=50)
        self.assertEqual(car.loc, -50)
        self.assertIs(car.direction, Direction.LEFT)


class TestChangeSpeed(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.car = place_car(self.world, self.world.lane_segment("h1", "right"),
                             speed=10, max_speed=20)

    def test_a_positive_difference_accelerates(self):
        self.car.change_speed(5)
        self.assertEqual(self.car.speed, 15)

    def test_a_negative_difference_decelerates(self):
        self.car.change_speed(-4)
        self.assertEqual(self.car.speed, 6)

    def test_zero_leaves_the_speed_alone(self):
        self.car.change_speed(0)
        self.assertEqual(self.car.speed, 10)

    def test_speed_is_clamped_at_the_cars_maximum(self):
        self.car.change_speed(1000)
        self.assertEqual(self.car.speed, 20)

    def test_speed_never_goes_below_zero(self):
        self.car.change_speed(-1000)
        self.assertEqual(self.car.speed, 0)

    def test_the_segment_limit_is_not_enforced_here(self):
        """`change_speed` clamps only against the car's own max_speed.

        Staying under a *segment's* limit is the controllers' job (see
        `AstarCarController.get_accelerate`), which is why an action applied
        directly can exceed a crossing's limit.
        """
        self.car.max_speed = LANE_MAX_SPEED
        self.car.change_speed(LANE_MAX_SPEED)
        self.assertGreater(self.car.speed, CROSSING_MAX_SPEED)


class TestBrakingDistance(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.car = place_car(self.world, self.world.lane_segment("h1", "right"),
                             speed=10, size=40, max_speed=20)

    def test_a_stationary_car_still_reserves_its_body_and_buffer(self):
        self.assertEqual(self.car.get_braking_distance(0), self.car.size + BUFFER)

    def test_the_distance_is_the_sum_of_the_speeds_while_braking_out(self):
        # From 11, braking at MAX_DEC per tick covers 11 then 1.
        self.assertEqual(self.car.get_braking_distance(11),
                         self.car.size + 11 + 1 + BUFFER)

    def test_a_speed_that_is_a_multiple_of_the_deceleration_stops_exactly(self):
        self.assertEqual(self.car.get_braking_distance(2 * MAX_DEC),
                         self.car.size + 2 * MAX_DEC + MAX_DEC + BUFFER)

    def test_it_defaults_to_the_cars_current_speed(self):
        self.assertEqual(self.car.get_braking_distance(),
                         self.car.get_braking_distance(self.car.speed))

    def test_it_grows_monotonically_with_speed(self):
        distances = [self.car.get_braking_distance(v) for v in range(0, 21)]
        self.assertEqual(distances, sorted(distances))

    def test_a_bigger_car_needs_more_room(self):
        big = place_car(self.world, self.world.lane_segment("v1", "right"),
                        size=80, name="Big")
        self.assertEqual(big.get_braking_distance(10) - self.car.get_braking_distance(10),
                         big.size - self.car.size)

    def test_a_negative_speed_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.car.get_braking_distance(-1)
        self.assertIn("non-negative", str(ctx.exception))

    def test_a_dead_car_reports_its_speed_and_ignores_the_argument(self):
        """FLAGGED (FINDINGS #14): the `speed` argument is discarded once dead.

        A wreck is frozen at speed 0 by `handle_car_death`, so this returns 0 --
        a dead car reserves nothing beyond what `handle_car_death` already left
        it. The argument being silently ignored is the surprising part; no live
        caller reaches it, because `safety_checks.max_end_growth` tests for
        death first.
        """
        self.car.handle_car_death(self.world.reservation_management)
        self.assertEqual(self.car.get_braking_distance(15), self.car.speed)
        self.assertEqual(self.car.get_braking_distance(15), 0)


class TestMove(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_a_move_advances_the_offset_by_the_speed(self):
        car = place_car(self.world, self.segment, speed=10)
        car.move(self.rm)
        self.assertEqual(car.loc, 10)

    def test_a_move_advances_the_cars_clock(self):
        car = place_car(self.world, self.segment, speed=10)
        car.move(self.rm)
        car.move(self.rm)
        self.assertEqual(car.time, 2)

    def test_a_stationary_car_still_ticks(self):
        car = place_car(self.world, self.segment, speed=0)
        car.move(self.rm)
        self.assertEqual((car.loc, car.time), (0, 1))

    def test_a_move_reports_success(self):
        car = place_car(self.world, self.segment, speed=5)
        self.assertTrue(car.move(self.rm))

    def test_a_reverse_lane_car_moves_backwards_along_the_axis(self):
        reverse = self.world.lane_segment("h1", "left")
        car = place_car(self.world, reverse, speed=10)
        car.move(self.rm)
        self.assertEqual(car.loc, -10)

    def test_the_reservation_rear_follows_the_car(self):
        car = place_car(self.world, self.segment, speed=10)
        car.move(self.rm)
        self.assertEqual(self.rm.get_car_reservation(car.id, 0).begin, car.loc)

    def test_the_reservation_end_stays_a_braking_distance_ahead(self):
        car = place_car(self.world, self.segment, speed=10, size=40)
        car.move(self.rm)
        info = self.rm.get_car_reservation(car.id, 0)
        self.assertEqual(abs(info.end) - abs(info.begin), car.get_braking_distance())

    def test_the_position_is_refreshed_after_a_move(self):
        car = place_car(self.world, self.segment, speed=10)
        before = car.pos.x
        car.move(self.rm)
        self.assertEqual(car.pos.x, before + 10)

    def test_a_dead_car_does_not_move(self):
        car = place_car(self.world, self.segment, speed=10)
        car.handle_car_death(self.rm)
        self.assertFalse(car.move(self.rm))
        self.assertEqual((car.loc, car.time), (0, 0))

    def test_a_car_leaves_a_segment_once_it_runs_past_its_length(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(25):
            car.move(self.rm)
        self.assertNotIn(self.segment, reservation_segments(self.world, car))

    def test_the_offset_is_rebased_when_a_segment_is_left_behind(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(25):
            car.move(self.rm)
            head = self.rm.get_car_reservation(car.id, 0)
            self.assertLessEqual(abs(car.loc), head.segment.length)


class TestReservationExtension(unittest.TestCase):
    """A car reserves ahead into the crossing it is approaching."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, speed=10, size=40,
                             goal_segment=self.world.lane_segment("v1", "right"))

    def _drive(self, ticks):
        for _ in range(ticks):
            self.car.move(self.rm)

    def test_a_car_far_from_the_end_holds_only_its_own_segment(self):
        self._drive(3)
        self.assertEqual(reservation_segments(self.world, self.car), [self.segment])

    def test_approaching_the_end_extends_into_the_crossing_and_beyond(self):
        self._drive(13)
        held = reservation_segments(self.world, self.car)
        self.assertGreater(len(held), 1)
        self.assertTrue(any(isinstance(s, CrossingSegment) for s in held))

    def test_the_extension_ends_on_a_lane_segment(self):
        self._drive(13)
        held = reservation_segments(self.world, self.car)
        self.assertIsInstance(held[-1], LaneSegment)

    def test_a_crossing_reservation_records_a_departure_time(self):
        self._drive(13)
        for info in self.rm.get_car_reservations(self.car.id):
            if isinstance(info.segment, CrossingSegment):
                self.assertIsNotNone(
                    info.segment.crossing_segment_state.get_time_to_leave(self.car.id))

    def test_a_turn_into_a_new_direction_is_marked(self):
        self._drive(13)
        infos = self.rm.get_car_reservations(self.car.id)
        turning = [i for i in infos if i.turn]
        self.assertTrue(turning, "entering the vertical road is a turn")

    def test_every_reservation_but_the_last_spans_its_whole_segment(self):
        self._drive(13)
        infos = self.rm.get_car_reservations(self.car.id)
        for info in infos[:-1]:
            self.assertEqual(abs(info.end), info.segment.length)

    def test_the_car_occupies_every_segment_it_reserves(self):
        self._drive(13)
        for segment in reservation_segments(self.world, self.car):
            self.assertIn(self.car.id, self.rm.get_cars_on_segment(segment))


class TestCrossingClaim(unittest.TestCase):
    """`_update_crossing_claim`: register on approach, renew, release on entry."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.state = self.segment.end_crossing.intersection.intersection_state
        self.car = place_car(self.world, self.segment, speed=10, size=40,
                             goal_segment=self.world.lane_segment("v1", "right"))

    def test_a_car_far_from_the_intersection_holds_no_claim(self):
        self.car.move(self.rm)
        self.assertIsNone(self.state.get_car_priority(self.car.id))

    def test_a_claim_is_registered_once_the_reservation_nears_the_end(self):
        claimed_at = None
        for _ in range(12):
            self.car.move(self.rm)
            if self.state.get_car_priority(self.car.id) is not None:
                claimed_at = self.car.time
                break
        self.assertIsNotNone(claimed_at, "the car never claimed the intersection")

    def test_the_claim_keeps_the_tick_it_was_first_made_on(self):
        for _ in range(12):
            self.car.move(self.rm)
            if self.state.get_car_priority(self.car.id) is not None:
                break
        first = self.state.get_car_priority(self.car.id)
        self.car.move(self.rm)
        self.assertEqual(self.state.get_car_priority(self.car.id), first)

    def test_the_claim_is_released_when_the_car_reserves_into_the_crossing(self):
        for _ in range(14):
            self.car.move(self.rm)
        held = reservation_segments(self.world, self.car)
        if any(isinstance(s, CrossingSegment) for s in held):
            self.assertIsNone(self.state.get_car_priority(self.car.id))

    def test_a_lane_segment_with_no_crossing_ahead_never_claims(self):
        # Nothing to claim: the world's lane segments all lead into a crossing,
        # so build the degenerate case directly.
        info = self.rm.get_car_reservation(self.car.id, 0)
        original, info.segment.end_crossing = info.segment.end_crossing, None
        try:
            self.car._update_crossing_claim(self.rm)
            self.assertIsNone(self.state.get_car_priority(self.car.id))
        finally:
            info.segment.end_crossing = original


class TestAdjacentLaneSegments(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right", num=0)
        self.car = place_car(self.world, self.segment, speed=5)

    def test_every_parallel_lane_is_listed_including_the_cars_own(self):
        segments = self.car.get_adjacent_lane_segments(self.rm)
        self.assertEqual(len(segments), len(self.world.road("h1").right_lanes))
        self.assertIn(self.segment, segments)

    def test_the_listed_segments_all_share_a_segment_number(self):
        segments = self.car.get_adjacent_lane_segments(self.rm)
        self.assertEqual({s.num for s in segments}, {self.segment.num})

    def test_a_single_step_left_finds_the_next_lane(self):
        target = self.car.get_adjacent_lane_segment(self.rm, 1)
        self.assertIs(target, self.world.lane_segment("h1", "right", num=1))

    def test_a_step_off_the_road_gives_nothing(self):
        self.assertIsNone(self.car.get_adjacent_lane_segment(self.rm, -1))

    def test_a_step_of_zero_returns_the_cars_own_segment(self):
        self.assertIs(self.car.get_adjacent_lane_segment(self.rm, 0), self.segment)

    def test_an_explicit_segment_overrides_the_reservation(self):
        other = self.world.lane_segment("h1", "right", num=1)
        self.assertIs(self.car.get_adjacent_lane_segment(self.rm, -1, other),
                      self.segment)

    def test_lane_steps_are_mirrored_on_a_reverse_lane(self):
        """`lane_diff` is relative to the driver, not to the road's numbering."""
        reverse = self.world.lane_segment("h1", "left", num=0)
        car = place_car(self.world, reverse, speed=5, name="Rev")
        self.assertIsNone(car.get_adjacent_lane_segment(self.rm, 1))

    def test_a_car_on_a_crossing_has_no_adjacent_lane(self):
        world = single_crossing_world()
        rm = world.reservation_management
        car = place_car(world, world.lane_segment("h1", "right"), speed=10, size=40,
                        goal_segment=world.lane_segment("v1", "right"))
        for _ in range(25):
            car.move(rm)
            if isinstance(rm.get_car_reservation(car.id, 0).segment, CrossingSegment):
                break
        else:
            self.skipTest("the car never reached a crossing")
        self.assertIsNone(car.get_adjacent_lane_segments(rm))
        self.assertIsNone(car.get_adjacent_lane_segment(rm, 1))


class TestChangeLane(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right", num=0)
        self.car = place_car(self.world, self.segment, speed=5, size=40)

    def test_a_valid_change_is_accepted_and_registered(self):
        self.assertTrue(self.car.change_lane(self.rm, 1))
        self.assertTrue(self.car.changing_lane)
        claim = self.rm.get_lane_change_claim(self.car.id)
        self.assertEqual(claim.claimed_at, self.car.time)
        self.assertIs(claim.segment, self.world.lane_segment("h1", "right", num=1))

    def test_a_new_change_is_registered_as_an_uncommitted_claim(self):
        self.car.change_lane(self.rm, 1)
        self.assertFalse(self.rm.get_lane_change_claim(self.car.id).committed)

    def test_a_zero_step_is_refused_without_being_a_problem(self):
        self.assertIs(self.car.change_lane(self.rm, 0), False)
        self.assertIsNone(self.car.changing_lane)

    def test_a_step_off_the_road_reports_no_adjacent_lane(self):
        self.assertIs(self.car.change_lane(self.rm, -1), Problem.NO_ADJACENT_LANE)

    def test_a_single_lane_road_reports_no_adjacent_lane_either_way(self):
        world = single_crossing_world()
        car = place_car(world, world.lane_segment("h1", "right"), speed=5)
        for step in (1, -1):
            self.assertIs(car.change_lane(world.reservation_management, step),
                          Problem.NO_ADJACENT_LANE)

    def test_changing_lane_while_straddling_a_crossing_is_refused(self):
        world = single_crossing_world()
        rm = world.reservation_management
        car = place_car(world, world.lane_segment("h1", "right"), speed=10, size=40,
                        goal_segment=world.lane_segment("v1", "right"))
        for _ in range(14):
            car.move(rm)
        self.assertGreater(len(rm.get_car_reservations(car.id)), 1)
        self.assertIs(car.change_lane(rm, 1), Problem.CHANGE_LANE_WHILE_CROSSING)

    def test_an_occupied_target_lane_is_claimed_all_the_same(self):
        """A claim is deliberately blind: seeing the blocker is the
        controller's job over the next CLAIM_TIME ticks, not the car's now."""
        place_car(self.world, self.world.lane_segment("h1", "right", num=1),
                  loc=0, speed=0, size=40, name="Block")
        self.assertTrue(self.car.change_lane(self.rm, 1))
        self.assertTrue(self.car.changing_lane)

    def test_a_second_claim_is_refused_while_one_is_running(self):
        self.assertTrue(self.car.change_lane(self.rm, 1))
        self.assertIs(self.car.change_lane(self.rm, 1), False)
        self.assertIs(self.rm.get_lane_change_claim(self.car.id).segment,
                      self.world.lane_segment("h1", "right", num=1))


class TestWithdrawClaim(unittest.TestCase):
    """A claim may be given back until it commits, and not afterwards."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.source = self.world.lane_segment("h1", "right", num=0)
        self.target = self.world.lane_segment("h1", "right", num=1)
        self.car = place_car(self.world, self.source, speed=5, size=40)

    def test_withdrawing_with_no_claim_pending_does_nothing(self):
        self.assertIs(self.car.withdraw_claim(self.rm), False)

    def test_a_pending_claim_is_given_back(self):
        self.car.change_lane(self.rm, 1)
        self.assertIs(self.car.withdraw_claim(self.rm), True)
        self.assertFalse(self.car.changing_lane)
        self.assertIsNone(self.rm.get_lane_change_claim(self.car.id))

    def test_the_target_segment_is_free_again(self):
        self.car.change_lane(self.rm, 1)
        self.car.withdraw_claim(self.rm)
        self.assertEqual(self.rm.get_cars_changing_into_segment(self.target), [])

    def test_the_car_keeps_driving_on_its_own_lane(self):
        self.car.change_lane(self.rm, 1)
        self.car.withdraw_claim(self.rm)
        for _ in range(CLAIM_TIME + LANECHANGE_TIME_STEPS + 1):
            self.car.move(self.rm)
        self.assertEqual(reservation_segments(self.world, self.car), [self.source])

    def test_withdrawing_is_still_possible_on_the_last_claim_tick(self):
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME - 1):
            self.car.move(self.rm)
        self.assertIs(self.car.withdraw_claim(self.rm), True)

    def test_a_committed_change_can_no_longer_be_withdrawn(self):
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME + 1):
            self.car.move(self.rm)
        self.assertTrue(self.rm.get_lane_change_claim(self.car.id).committed)
        self.assertIs(self.car.withdraw_claim(self.rm), False)
        self.assertTrue(self.car.changing_lane)

    def test_a_car_that_dies_holding_a_claim_releases_the_lane(self):
        self.car.change_lane(self.rm, 1)
        self.car.handle_car_death(self.rm)
        self.assertEqual(self.rm.get_cars_changing_into_segment(self.target), [])
        self.assertFalse(self.car.changing_lane)


class TestCheckReservation(unittest.TestCase):
    """The claim commits after `CLAIM_TIME` and the car lands
    `LANECHANGE_TIME_STEPS` after that."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.source = self.world.lane_segment("h1", "right", num=0)
        self.target = self.world.lane_segment("h1", "right", num=1)
        self.car = place_car(self.world, self.source, speed=5, size=40)

    def _complete_change(self):
        """Drive until the registered lane change has been applied."""
        for _ in range(CLAIM_TIME + LANECHANGE_TIME_STEPS + 1):
            self.car.move(self.rm)

    def test_a_car_not_changing_lane_reports_false(self):
        """FIXED (FINDINGS #5): this path used to fall off the end as None."""
        self.assertIs(self.car.check_reservation(self.rm), False)

    def test_a_change_in_progress_but_not_yet_due_reports_false(self):
        self.car.change_lane(self.rm, 1)
        self.assertIs(self.car.check_reservation(self.rm), False)

    def test_the_change_is_still_pending_until_the_clock_reaches_the_deadline(self):
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME + LANECHANGE_TIME_STEPS):
            self.assertTrue(self.car.changing_lane)
            self.car.move(self.rm)
        self.assertEqual(self.car.time, CLAIM_TIME + LANECHANGE_TIME_STEPS)
        self.assertTrue(self.car.changing_lane,
                        "the change is applied by the move that starts on the deadline")

    def test_the_claim_stays_uncommitted_for_the_whole_claim_phase(self):
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME):
            self.assertFalse(self.rm.get_lane_change_claim(self.car.id).committed)
            self.car.move(self.rm)

    def test_the_claim_commits_on_the_move_that_starts_at_claim_time(self):
        # `check_reservation` runs at the top of `move`, before the clock is
        # advanced, so the claim commits during the (CLAIM_TIME + 1)th move --
        # the first one to begin with `car.time == CLAIM_TIME`.
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME + 1):
            self.car.move(self.rm)
        self.assertTrue(self.rm.get_lane_change_claim(self.car.id).committed)

    def test_the_car_is_still_on_the_source_lane_when_the_claim_commits(self):
        self.car.change_lane(self.rm, 1)
        for _ in range(CLAIM_TIME + 1):
            self.car.move(self.rm)
        self.assertEqual(reservation_segments(self.world, self.car), [self.source])

    def test_the_change_lands_on_the_move_that_starts_at_the_deadline(self):
        # Claim phase and change phase run back to back, so the car lands
        # during the (CLAIM_TIME + LANECHANGE_TIME_STEPS + 1)th move.
        self.car.change_lane(self.rm, 1)
        self._complete_change()
        self.assertFalse(self.car.changing_lane)

    def test_the_car_ends_up_on_the_target_segment(self):
        self.car.change_lane(self.rm, 1)
        self._complete_change()
        self.assertEqual(reservation_segments(self.world, self.car), [self.target])

    def test_the_source_segment_is_released(self):
        self.car.change_lane(self.rm, 1)
        self._complete_change()
        self.assertNotIn(self.car.id, self.rm.get_cars_on_segment(self.source))

    def test_the_pending_change_is_cleared_once_it_lands(self):
        self.car.change_lane(self.rm, 1)
        self._complete_change()
        self.assertIsNone(self.rm.get_lane_change_claim(self.car.id))

    def test_the_offset_carries_across_unchanged(self):
        self.car.change_lane(self.rm, 1)
        self._complete_change()
        self.assertEqual(self.rm.get_car_reservation(self.car.id, 0).begin, self.car.loc)


class TestGetSizeSegments(unittest.TestCase):
    """The car's *body*, as opposed to the space it has reserved ahead."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_a_car_inside_one_segment_occupies_only_that_segment(self):
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        footprint = car.get_size_segments(self.rm)
        self.assertEqual(len(footprint), 1)
        self.assertIs(footprint[0].segment, self.segment)

    def test_the_footprint_is_exactly_the_cars_size_long(self):
        car = place_car(self.world, self.segment, loc=0, speed=0, size=40)
        footprint = car.get_size_segments(self.rm)
        span = sum(abs(f.end - f.begin) for f in footprint)
        self.assertEqual(span, car.size)

    def test_the_footprint_starts_where_the_car_is(self):
        car = place_car(self.world, self.segment, loc=30, speed=0, size=40)
        self.assertEqual(car.get_size_segments(self.rm)[0].begin, car.loc)

    def test_a_reverse_lane_footprint_runs_the_other_way(self):
        reverse = self.world.lane_segment("h1", "left")
        car = place_car(self.world, reverse, loc=100, speed=0, size=40)
        footprint = car.get_size_segments(self.rm)[0]
        self.assertLess(footprint.end, footprint.begin)

    def test_a_straddling_car_reports_every_segment_it_covers(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(30):
            car.move(self.rm)
            footprint = car.get_size_segments(self.rm)
            self.assertEqual(sum(abs(f.end - f.begin) for f in footprint) >= car.size,
                             True)


class TestDeath(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")

    def test_a_dead_car_is_stopped_and_marked(self):
        car = place_car(self.world, self.segment, speed=15)
        car.handle_car_death(self.rm)
        self.assertTrue(car.get_death_status())
        self.assertEqual(car.speed, 0)

    def test_a_wreck_keeps_only_the_segments_its_body_covers(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(13):
            car.move(self.rm)
        self.assertGreater(len(self.rm.get_car_reservations(car.id)), 1)
        car.handle_car_death(self.rm)
        self.assertEqual(len(self.rm.get_car_reservations(car.id)),
                         len(car.get_size_segments(self.rm)))

    def test_the_space_ahead_is_given_back(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(13):
            car.move(self.rm)
        released = [s for s in reservation_segments(self.world, car)][1:]
        car.handle_car_death(self.rm)
        for segment in released:
            self.assertNotIn(car.id, self.rm.get_cars_on_segment(segment))

    def test_a_wreck_holds_no_intersection_claim(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        state = self.segment.end_crossing.intersection.intersection_state
        for _ in range(11):
            car.move(self.rm)
        car.handle_car_death(self.rm)
        self.assertIsNone(state.get_car_priority(car.id),
                          "a wreck must not hold an intersection closed forever")

    def test_a_wreck_on_a_crossing_never_leaves_it(self):
        car = place_car(self.world, self.segment, speed=10, size=40,
                        goal_segment=self.world.lane_segment("v1", "right"))
        for _ in range(30):
            car.move(self.rm)
            if isinstance(self.rm.get_car_reservation(car.id, 0).segment, CrossingSegment):
                break
        else:
            self.skipTest("the car never occupied a crossing")
        car.handle_car_death(self.rm)
        for info in self.rm.get_car_reservations(car.id):
            if isinstance(info.segment, CrossingSegment):
                self.assertEqual(
                    info.segment.crossing_segment_state.get_time_to_leave(car.id),
                    float("inf"))

    def test_dying_twice_is_harmless(self):
        car = place_car(self.world, self.segment, speed=10)
        car.handle_car_death(self.rm)
        car.handle_car_death(self.rm)
        self.assertTrue(car.get_death_status())


class TestPositionReporting(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management

    def test_a_horizontal_car_is_as_wide_as_its_size_and_a_lane_tall(self):
        car = place_car(self.world, self.world.lane_segment("h1", "right"), size=44)
        self.assertEqual((car.w, car.h), (44, BLOCK_SIZE))

    def test_a_vertical_car_is_a_lane_wide_and_as_tall_as_its_size(self):
        car = place_car(self.world, self.world.lane_segment("v1", "right"), size=44)
        self.assertEqual((car.w, car.h), (BLOCK_SIZE, 44))

    def test_a_forward_car_is_anchored_at_its_reference_point(self):
        segment = self.world.lane_segment("h1", "right")
        car = place_car(self.world, segment, loc=30, size=40)
        self.assertEqual(car.pos.x, segment.begin + 30)
        self.assertEqual(car.pos.y, segment.lane.top)

    def test_a_reverse_car_is_anchored_a_body_length_back(self):
        segment = self.world.lane_segment("h1", "left")
        car = place_car(self.world, segment, loc=30, size=40)
        self.assertEqual(car.pos.x, segment.begin - 30 - car.size)

    def test_get_position_reports_the_bottom_left_corner_and_extent(self):
        car = place_car(self.world, self.world.lane_segment("h1", "right"),
                        loc=20, size=40)
        self.assertEqual(car.get_position(), (car.pos.x, car.pos.y, car.w, car.h))

    def test_the_centre_of_a_horizontal_car_is_half_a_body_along(self):
        car = place_car(self.world, self.world.lane_segment("h1", "right"),
                        loc=20, size=40)
        self.assertEqual(car.get_center(self.rm),
                         [car.pos.x + car.size // 2, car.pos.y + BLOCK_SIZE // 2])

    def test_the_centre_of_a_vertical_car_swaps_the_axes(self):
        car = place_car(self.world, self.world.lane_segment("v1", "right"),
                        loc=20, size=40)
        self.assertEqual(car.get_center(self.rm),
                         [car.pos.x + BLOCK_SIZE // 2, car.pos.y + car.size // 2])


class TestAstar(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.start = self.world.lane_segment("h1", "right")
        self.goal_segment = self.world.lane_segment("v1", "right")
        self.car = place_car(self.world, self.start, speed=10,
                             goal_segment=self.goal_segment)

    def test_a_path_starts_where_the_car_is_and_ends_at_the_goal(self):
        path = self.car.astar(self.rm)
        self.assertIs(path[0], self.start)
        self.assertIs(path[-1], self.goal_segment)

    def test_a_path_alternates_lane_segments_and_crossings(self):
        path = self.car.astar(self.rm)
        for segment in path:
            self.assertIsInstance(segment, (LaneSegment, CrossingSegment))

    def test_consecutive_segments_are_actually_connected(self):
        path = self.car.astar(self.rm)
        for current, following in zip(path, path[1:]):
            if isinstance(current, LaneSegment):
                self.assertIs(current.end_crossing, following)
            else:
                self.assertIn(following, current.connected_segments.values())

    def test_a_goal_on_the_current_segment_is_a_one_step_path(self):
        car = place_car(self.world, self.start, speed=0, name="Home",
                        goal_segment=self.start)
        self.assertEqual(car.astar(self.rm), [self.start])

    def test_an_explicit_start_segment_is_honoured(self):
        other = self.world.lane_segment("v1", "left")
        path = self.car.astar(self.rm, start_seg=other)
        self.assertIs(path[0], other)

    def test_an_explicit_goal_is_honoured(self):
        target = self.world.lane_segment("h1", "left")
        path = self.car.astar(self.rm, goal=Goal(target, TEST_COLOR))
        self.assertIs(path[-1], target)

    def test_an_unreachable_goal_gives_an_empty_path(self):
        # A second, disconnected world's segment can never be reached.
        elsewhere = single_crossing_world().lane_segment("h1", "right")
        self.assertEqual(self.car.astar(self.rm, goal=Goal(elsewhere, TEST_COLOR)), [])

    def test_the_ring_world_has_exactly_one_route(self):
        world = ring_world()
        start = world.lane_segment("hb", "right")
        target = world.lane_segment("ht", "left")
        car = place_car(world, start, speed=5, goal_segment=target)
        path = car.astar(world.reservation_management)
        self.assertIs(path[0], start)
        self.assertIs(path[-1], target)
        self.assertEqual(len(path), len(set(id(s) for s in path)),
                         "a shortest path never repeats a segment")


class TestAstarSpeed(unittest.TestCase):
    """`Car.astar_speed` -- the congestion-aware planner. FINDINGS #11: unused.

    Nothing calls it (`get_next_segment` uses the length-only `astar`), so
    `ASTAR_CONGESTION_ALPHA` is inert too. Tested because it is a documented,
    exported behaviour that a future controller is meant to switch to.
    """

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.start = self.world.lane_segment("h1", "right")
        self.goal_segment = self.world.lane_segment("v1", "right")
        self.car = place_car(self.world, self.start, speed=10,
                             goal_segment=self.goal_segment)

    def test_it_finds_the_same_route_when_the_roads_are_empty(self):
        self.assertEqual([str(s) for s in self.car.astar_speed(self.rm)],
                         [str(s) for s in self.car.astar(self.rm)])

    def test_a_goal_on_the_current_segment_is_a_one_step_path(self):
        car = place_car(self.world, self.start, speed=0, name="Home",
                        goal_segment=self.start)
        self.assertEqual(car.astar_speed(self.rm), [self.start])

    def test_it_still_returns_a_plan_when_a_stopped_car_blocks_the_only_route(self):
        blocker = place_car(self.world, self.goal_segment, speed=0, name="Stalled")
        blocker.speed = 0
        path = self.car.astar_speed(self.rm, cars=[self.car, blocker])
        self.assertTrue(path, "the ignore_blocked fallback must still yield a plan")

    def test_it_accepts_a_car_list_and_ignores_ids_it_does_not_know(self):
        path = self.car.astar_speed(self.rm, cars=[])
        self.assertIs(path[-1], self.goal_segment)

    def test_an_unreachable_goal_gives_an_empty_path(self):
        elsewhere = single_crossing_world().lane_segment("h1", "right")
        self.assertEqual(
            self.car.astar_speed(self.rm, goal=Goal(elsewhere, TEST_COLOR)), [])


class TestGetNextSegment(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.start = self.world.lane_segment("h1", "right")

    def test_the_plan_starts_where_asked_and_ends_on_a_lane_segment(self):
        car = place_car(self.world, self.start, speed=10,
                        goal_segment=self.world.lane_segment("v1", "right"))
        plan = car.get_next_segment(self.rm)
        self.assertIs(plan[0], self.start)
        self.assertIsInstance(plan[-1], LaneSegment)

    def test_only_the_last_element_is_a_lane_segment(self):
        car = place_car(self.world, self.start, speed=10,
                        goal_segment=self.world.lane_segment("v1", "right"))
        plan = car.get_next_segment(self.rm)
        for segment in plan[1:-1]:
            self.assertIsInstance(segment, CrossingSegment)

    def test_a_car_already_on_its_goal_plans_towards_the_second_goal(self):
        second = self.world.lane_segment("h1", "left")
        car = place_car(self.world, self.start, speed=10,
                        goal_segment=self.start, second_goal_segment=second)
        plan = car.get_next_segment(self.rm)
        self.assertTrue(plan)
        self.assertIs(plan[0], self.start)

    def test_an_explicit_last_segment_is_planned_from(self):
        car = place_car(self.world, self.start, speed=10,
                        goal_segment=self.world.lane_segment("v1", "right"))
        other = self.world.lane_segment("v1", "left")
        plan = car.get_next_segment(self.rm, last_seg=other)
        self.assertIs(plan[0], other)

    def test_no_plan_is_the_empty_list_rather_than_none(self):
        """FIXED (FINDINGS #6): the two no-plan paths used to return None.

        The signature says `List[Segment]`, and callers spell the check
        `if not plan or len(plan) < 2`, so both no-plan cases are now [].
        """
        car = place_car(self.world, self.start, speed=10, name="Lost",
                        goal_segment=self.start)
        elsewhere = single_crossing_world().lane_segment("h1", "right")
        car.goal = Goal(elsewhere, TEST_COLOR)
        car.second_goal = Goal(elsewhere, TEST_COLOR)
        plan = car.get_next_segment(self.rm)
        self.assertEqual(plan, [])
        self.assertIsNotNone(plan, "no-plan must be [], never None")

    def test_a_plan_of_one_segment_is_also_reported_as_empty(self):
        car = place_car(self.world, self.start, speed=0, name="Arrived",
                        goal_segment=self.start, second_goal_segment=self.start)
        self.assertEqual(car.get_next_segment(self.rm, last_seg=self.start), [])


if __name__ == "__main__":
    unittest.main()
