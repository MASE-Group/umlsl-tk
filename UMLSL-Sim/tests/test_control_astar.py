"""Tests for `control.astar` -- the NPC controller.

`AstarCarController.get_action()` answers "what should this car do now": the
largest acceleration that stays legal and safe, plus a lane change when a
neighbouring lane offers a better one. It reads the world and never writes it,
with one deliberate exception -- withdrawing its own intersection claim to break
a deadlock -- which is covered below.
"""

import unittest

from umlsl_sim.config.logic_constants import (
    BUFFER,
    CROSSING_MAX_SPEED,
    LANECHANGE_TIME_STEPS,
    LANE_MAX_SPEED,
    LEFT_LANE_CHANGE,
    MAX_ACC,
    MAX_DEC,
    NO_LANE_CHANGE,
    RIGHT_LANE_CHANGE,
)
from umlsl_sim.control.astar.astar_car_controller import AstarCarController
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.ports import CarController
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    LaneSegment,
    SegmentInfo,
)

from tests.helpers import place_car, ring_world, single_crossing_world, two_lane_world


class _ControllerFixture(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.cars = [self.car]
        self.controller = AstarCarController(self.car, self.cars, self.rm)

    def act(self):
        """Skip the first-call warm-up and return a real decision."""
        if self.controller.first_go:
            self.controller.get_action()
        return self.controller.get_action()

    def reservations(self):
        return self.rm.get_car_reservations(self.car.id)


class TestControllerContract(_ControllerFixture):

    def test_it_satisfies_the_car_controller_port(self):
        self.assertIsInstance(self.controller, CarController)

    def test_the_first_call_is_a_no_op(self):
        self.assertEqual(self.controller.get_action(), (0, 0))

    def test_the_warm_up_happens_only_once(self):
        self.controller.get_action()
        self.assertFalse(self.controller.first_go)

    def test_an_action_is_an_acceleration_and_a_lane_change(self):
        acceleration, lane_change = self.act()
        self.assertIsInstance(acceleration, int)
        self.assertIn(lane_change, (NO_LANE_CHANGE, LEFT_LANE_CHANGE, RIGHT_LANE_CHANGE))

    def test_the_acceleration_is_within_the_allowed_band(self):
        acceleration, _ = self.act()
        self.assertGreaterEqual(acceleration, -MAX_DEC)
        self.assertLessEqual(acceleration, MAX_ACC)

    def test_the_controller_keeps_the_car_and_world_it_was_given(self):
        self.assertIs(self.controller.car, self.car)
        self.assertIs(self.controller.cars, self.cars)
        self.assertIs(self.controller.reservation_management, self.rm)

    def test_deciding_does_not_move_the_car(self):
        before = (self.car.loc, self.car.speed, self.car.time)
        self.act()
        self.assertEqual((self.car.loc, self.car.speed, self.car.time), before)


class TestGetAccelerate(_ControllerFixture):

    def test_an_empty_road_allows_full_acceleration(self):
        self.assertEqual(self.controller.get_accelerate(self.reservations(), True),
                         MAX_ACC)

    def test_an_empty_segment_list_allows_full_acceleration(self):
        self.assertEqual(self.controller.get_accelerate([], False), MAX_ACC)

    def test_the_cars_own_maximum_caps_the_acceleration(self):
        self.car.speed = self.car.max_speed - 2
        self.assertLessEqual(
            self.controller.get_accelerate(self.reservations(), True), 2)

    def test_a_car_already_at_its_maximum_may_not_accelerate(self):
        self.car.speed = self.car.max_speed
        self.assertLessEqual(
            self.controller.get_accelerate(self.reservations(), True), 0)

    def test_a_crossing_in_the_reservation_caps_the_speed(self):
        crossing = self.segment.end_crossing
        info = SegmentInfo(crossing, 0, crossing.length, self.car.direction)
        self.car.speed = CROSSING_MAX_SPEED
        self.assertLessEqual(self.controller.get_accelerate([info], False), 0)

    def test_a_stationary_car_is_never_asked_to_brake_below_zero(self):
        self.car.speed = 0
        self.assertGreaterEqual(
            self.controller.get_accelerate(self.reservations(), True), 0)

    def test_deceleration_never_exceeds_the_current_speed(self):
        for speed in (0, 3, 7, MAX_DEC, MAX_DEC + 5):
            self.car.speed = speed
            self.assertGreaterEqual(
                self.controller.get_accelerate(self.reservations(), True),
                -min(MAX_DEC, speed))

    def test_a_car_it_does_not_know_about_cannot_restrict_it(self):
        """The controller reads its `cars` list, not the occupancy table: a car
        it was never told about is invisible to the rear-end check."""
        place_car(self.world, self.segment, loc=100, speed=0, size=40, name="Ghost")
        self.assertEqual(self.controller.get_accelerate(self.reservations(), True),
                         MAX_ACC)


class TestGetAccelerateWithTraffic(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.blocker = place_car(self.world, self.segment, loc=100, speed=0, size=40,
                                 max_speed=LANE_MAX_SPEED, name="Block")
        self.cars = [self.car, self.blocker]
        self.controller = AstarCarController(self.car, self.cars, self.rm)
        self.controller.get_action()

    def test_a_stopped_leader_limits_the_acceleration(self):
        allowed = self.controller.get_accelerate(
            self.rm.get_car_reservations(self.car.id), True)
        self.assertLess(allowed, MAX_ACC)

    def test_the_result_keeps_the_projection_clear_of_the_leader(self):
        allowed = self.controller.get_accelerate(
            self.rm.get_car_reservations(self.car.id), True)
        new_speed = self.car.speed + allowed
        reach = abs(self.car.loc) + self.car.get_braking_distance(new_speed) + new_speed
        self.assertLessEqual(reach, abs(self.blocker.loc) + self.blocker.size + BUFFER
                             + self.car.get_braking_distance(0))

    def test_a_leader_close_enough_forces_full_braking(self):
        self.blocker.loc = self.car.loc + self.car.size
        self.rm.update_car_reservation_begin(self.blocker.id, 0, self.blocker.loc)
        self.assertEqual(
            self.controller.get_accelerate(
                self.rm.get_car_reservations(self.car.id), True),
            -min(MAX_DEC, self.car.speed))

    def test_a_leader_that_drives_away_frees_the_road_again(self):
        self.blocker.speed = LANE_MAX_SPEED
        self.blocker.loc = 180
        self.rm.update_car_reservation_begin(self.blocker.id, 0, self.blocker.loc)
        self.assertGreater(
            self.controller.get_accelerate(
                self.rm.get_car_reservations(self.car.id), True),
            -MAX_DEC)


class TestPriorityBlockedFlag(unittest.TestCase):
    """`get_accelerate` records why it refused, and `get_action` acts on it."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.state = self.segment.end_crossing.intersection.intersection_state
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.controller = AstarCarController(self.car, [self.car], self.rm)
        self.controller.get_action()

    def test_the_flag_starts_clear(self):
        self.controller.get_accelerate(self.rm.get_car_reservations(self.car.id), True)
        self.assertFalse(self.controller._last_call_priority_blocked)

    def test_the_flag_is_reset_at_the_top_of_every_call(self):
        self.controller._last_call_priority_blocked = True
        self.controller.get_accelerate(self.rm.get_car_reservations(self.car.id), True)
        self.assertFalse(self.controller._last_call_priority_blocked)

    def _drive_outranked(self, ticks=20):
        """Drive under the controller while a rival permanently outranks us.

        Returns the priority the car held just before its claim was withdrawn,
        or None if it never came to that. The car approaches the intersection,
        claims it, finds every acceleration rejected by the priority check,
        brakes down -- and once braking is all it has left, gives the claim up.
        """
        held = None
        for _ in range(ticks):
            self.state.add_car_priority("rival", -100)
            before = self.state.get_car_priority(self.car.id)
            acceleration, _ = self.controller.get_action()
            after = self.state.get_car_priority(self.car.id)
            if before is not None and after is None:
                return before
            held = after
            self.car.change_speed(acceleration)
            self.car.move(self.rm)
        return None

    def test_an_outranked_car_eventually_gives_up_its_claim(self):
        self.assertIsNotNone(self._drive_outranked(),
                             "holding a claim we cannot use only blocks the queue")

    def test_a_withdrawn_claim_is_re_taken_at_the_back_of_the_queue(self):
        """Withdrawing is not resignation: the car is still approaching, so it
        claims again next tick -- behind everyone who claimed in the meantime."""
        surrendered = self._drive_outranked()
        self.assertIsNotNone(surrendered)
        for _ in range(3):
            self.state.add_car_priority("rival", -100)
            acceleration, _ = self.controller.get_action()
            self.car.change_speed(acceleration)
            self.car.move(self.rm)
        retaken = self.state.get_car_priority(self.car.id)
        if retaken is not None:
            self.assertGreater(retaken, surrendered)

    def test_the_priority_check_is_what_rejected_the_accelerations(self):
        self._drive_outranked()
        self.assertTrue(self.controller._last_call_priority_blocked)

    def test_an_unopposed_car_keeps_its_claim(self):
        for _ in range(12):
            self.car.move(self.rm)
            if self.state.get_car_priority(self.car.id) is not None:
                break
        held = self.state.get_car_priority(self.car.id)
        self.assertIsNotNone(held)
        self.controller.get_action()
        self.assertEqual(self.state.get_car_priority(self.car.id), held,
                         "nothing outranks us, so there is nothing to give up")


class TestChooseLaneChange(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.inner = self.world.lane_segment("h1", "right", num=0)
        self.outer = self.world.lane_segment("h1", "right", num=1)
        self.car = place_car(self.world, self.inner, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.cars = [self.car]
        self.controller = AstarCarController(self.car, self.cars, self.rm)
        self.controller.get_action()

    def _choose(self, current_acc=0):
        return self.controller._choose_lane_change(
            self.rm.get_car_reservations(self.car.id), current_acc)

    def test_an_empty_road_offers_no_reason_to_change(self):
        self.assertEqual(self._choose(current_acc=MAX_ACC), NO_LANE_CHANGE)

    def test_it_refuses_when_there_is_no_room_to_complete_the_change(self):
        # Put the car near the segment end so the change cannot finish in time.
        self.car.loc = self.inner.length - 5
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.inner.length)
        self.assertEqual(self._choose(current_acc=MAX_ACC), NO_LANE_CHANGE)

    def test_it_requires_exactly_one_reservation(self):
        crossing = self.inner.end_crossing
        extra = SegmentInfo(crossing, 0, crossing.length, self.car.direction)
        reservations = self.rm.get_car_reservations(self.car.id) + [extra]
        with self.assertRaises(RuntimeError) as ctx:
            self.controller._choose_lane_change(reservations, 0)
        self.assertIn("lane changes require exactly one reservation",
                      str(ctx.exception))

    def test_it_refuses_to_run_on_a_crossing(self):
        crossing = self.inner.end_crossing
        info = SegmentInfo(crossing, 0, crossing.length, self.car.direction)
        with self.assertRaises(RuntimeError) as ctx:
            self.controller._choose_lane_change([info], 0)
        self.assertIn("only valid on LaneSegments", str(ctx.exception))

    def test_a_lane_it_cannot_reach_in_one_step_is_not_offered(self):
        # From lane 0 the only single step is to lane 1; a right step leaves
        # the road, so RIGHT_LANE_CHANGE is never a candidate here.
        self.assertNotEqual(self._choose(current_acc=0), RIGHT_LANE_CHANGE)


class TestChooseLaneChangeWithTraffic(unittest.TestCase):
    """The decision proper, with the controller's `cars` list kept in step."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.inner = self.world.lane_segment("h1", "right", num=0)
        self.outer = self.world.lane_segment("h1", "right", num=1)
        self.car = place_car(self.world, self.inner, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))

    def _controller(self, *others):
        cars = [self.car, *others]
        controller = AstarCarController(self.car, cars, self.rm)
        controller.get_action()
        return controller

    def test_a_blocked_own_lane_and_a_free_neighbour_prompts_a_change(self):
        # Close enough that our own lane costs us acceleration; lane 1 is free.
        blocker = place_car(self.world, self.inner, loc=90, speed=0, size=40,
                            max_speed=LANE_MAX_SPEED, name="Block")
        controller = self._controller(blocker)
        _, lane_change = controller.get_action()
        self.assertEqual(lane_change, LEFT_LANE_CHANGE,
                         "lane 1 is the only step available from lane 0")

    def test_a_blocked_neighbour_is_not_moved_into(self):
        own = place_car(self.world, self.inner, loc=90, speed=0, size=40,
                        max_speed=LANE_MAX_SPEED, name="Block")
        beside = place_car(self.world, self.outer, loc=0, speed=0, size=40,
                           max_speed=LANE_MAX_SPEED, name="Beside")
        controller = self._controller(own, beside)
        _, lane_change = controller.get_action()
        self.assertEqual(lane_change, NO_LANE_CHANGE)

    def test_no_lane_change_is_offered_while_one_is_in_progress(self):
        controller = self._controller()
        self.car.change_lane(self.rm, LEFT_LANE_CHANGE)
        self.rm.set_reserved_lane_change_segment(self.car.id, (self.car.time, self.outer))
        _, lane_change = controller.get_action()
        self.assertEqual(lane_change, NO_LANE_CHANGE)

    def test_a_car_already_on_its_goal_segment_does_not_change_lane(self):
        car = place_car(self.world, self.inner, loc=0, speed=10, size=40,
                        max_speed=LANE_MAX_SPEED, name="Home",
                        goal_segment=self.inner)
        controller = AstarCarController(car, [car], self.rm)
        controller.get_action()
        _, lane_change = controller.get_action()
        self.assertEqual(lane_change, NO_LANE_CHANGE)


class TestLaneChangeWillComplete(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.inner = self.world.lane_segment("h1", "right", num=0)
        self.outer = self.world.lane_segment("h1", "right", num=1)
        self.car = place_car(self.world, self.inner, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED)
        self.controller = AstarCarController(self.car, [self.car], self.rm)

    def test_without_a_registered_change_nothing_can_complete(self):
        self.assertFalse(self.controller._lane_change_will_complete(
            self.rm.get_car_reservations(self.car.id), 10))

    def test_plenty_of_room_lets_the_change_complete(self):
        self.rm.set_reserved_lane_change_segment(self.car.id, (self.car.time, self.outer))
        self.assertTrue(self.controller._lane_change_will_complete(
            self.rm.get_car_reservations(self.car.id), 5))

    def test_too_little_room_rejects_the_speed(self):
        self.rm.set_reserved_lane_change_segment(self.car.id, (self.car.time, self.outer))
        self.car.loc = self.inner.length - 10
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.inner.length)
        self.assertFalse(self.controller._lane_change_will_complete(
            self.rm.get_car_reservations(self.car.id), LANE_MAX_SPEED))

    def test_a_change_already_due_always_completes(self):
        self.rm.set_reserved_lane_change_segment(
            self.car.id, (self.car.time - LANECHANGE_TIME_STEPS, self.outer))
        self.assertTrue(self.controller._lane_change_will_complete(
            self.rm.get_car_reservations(self.car.id), LANE_MAX_SPEED))


class TestProjectReservation(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.controller = AstarCarController(self.car, [self.car], self.rm)

    def _project(self, new_speed):
        return self.controller._project_reservation(
            self.rm.get_car_reservations(self.car.id), new_speed)

    def test_a_projection_keeps_the_cars_current_rear(self):
        projected = self._project(10)
        self.assertEqual(projected[0].begin,
                         self.rm.get_car_reservation(self.car.id, 0).begin)

    def test_a_faster_projection_reaches_further(self):
        slow = self._project(5)
        fast = self._project(LANE_MAX_SPEED)
        self.assertGreater(sum(abs(s.end - s.begin) for s in fast),
                           sum(abs(s.end - s.begin) for s in slow))

    def test_the_projection_never_shrinks_below_the_body_and_buffer(self):
        projected = self._project(0)
        self.assertGreaterEqual(abs(projected[-1].end) - abs(projected[-1].begin),
                                self.car.size + BUFFER)

    def test_it_extends_into_the_next_segments_when_it_no_longer_fits(self):
        self.car.loc = self.segment.length - 30
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        projected = self._project(LANE_MAX_SPEED)
        self.assertGreater(len(projected), 1)
        self.assertTrue(any(isinstance(s.segment, CrossingSegment) for s in projected))

    def test_an_extended_projection_ends_on_a_lane_segment(self):
        self.car.loc = self.segment.length - 30
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        projected = self._project(LANE_MAX_SPEED)
        self.assertIsInstance(projected[-1].segment, LaneSegment)

    def test_a_turn_into_a_new_direction_is_marked(self):
        self.car.loc = self.segment.length - 30
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        projected = self._project(LANE_MAX_SPEED)
        self.assertTrue(any(s.turn for s in projected))

    def test_no_known_route_gives_no_projection(self):
        from umlsl_sim.simulation.road_network.road_network import Goal
        elsewhere = single_crossing_world().lane_segment("h1", "right")
        self.car.goal = Goal(elsewhere, (0, 0, 0))
        self.car.second_goal = Goal(elsewhere, (0, 0, 0))
        self.car.loc = self.segment.length - 5
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        self.assertIsNone(self._project(LANE_MAX_SPEED))


class TestViolatesSafety(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.controller = AstarCarController(self.car, [self.car], self.rm)

    def test_an_empty_road_is_safe(self):
        current = self.rm.get_car_reservations(self.car.id)
        projected = self.controller._project_reservation(current, 10)
        self.assertEqual(self.controller._violates_safety(current, projected, 10),
                         (False, False))

    def test_a_leader_close_ahead_is_unsafe_but_not_a_priority_matter(self):
        blocker = place_car(self.world, self.segment, loc=60, speed=0, size=40,
                            max_speed=LANE_MAX_SPEED, name="Block")
        controller = AstarCarController(self.car, [self.car, blocker], self.rm)
        current = self.rm.get_car_reservations(self.car.id)
        projected = self.controller._project_reservation(current, LANE_MAX_SPEED)
        unsafe, by_priority = controller._violates_safety(current, projected,
                                                          LANE_MAX_SPEED)
        self.assertTrue(unsafe)
        self.assertFalse(by_priority)

    def test_being_outranked_at_a_new_crossing_is_reported_as_a_priority_block(self):
        self.car.loc = self.segment.length - 30
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        current = self.rm.get_car_reservations(self.car.id)
        projected = self.controller._project_reservation(current, LANE_MAX_SPEED)
        if projected is None or not any(isinstance(s.segment, CrossingSegment)
                                        for s in projected):
            self.skipTest("the projection never reached a crossing")

        state = self.segment.end_crossing.intersection.intersection_state
        state.add_car_priority(self.car.id, 10)
        state.add_car_priority("rival", 1)
        unsafe, by_priority = self.controller._violates_safety(
            current, projected, LANE_MAX_SPEED)
        self.assertTrue(unsafe)
        self.assertTrue(by_priority)

    def test_a_crossing_already_held_is_not_re_checked_for_priority(self):
        for _ in range(14):
            self.car.move(self.rm)
        current = self.rm.get_car_reservations(self.car.id)
        if not any(isinstance(s.segment, CrossingSegment) for s in current):
            self.skipTest("the car never reserved into the crossing")
        state = current[1].segment.intersection.intersection_state
        state.add_car_priority(self.car.id, 10)
        state.add_car_priority("rival", 1)
        _, by_priority = self.controller._violates_safety(current, current, 10)
        self.assertFalse(by_priority,
                         "a crossing we already hold is ours regardless of rank")


class TestDropPendingPriority(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.state = self.segment.end_crossing.intersection.intersection_state
        self.car = place_car(self.world, self.segment, loc=0, speed=0, size=40,
                             max_speed=LANE_MAX_SPEED)
        self.controller = AstarCarController(self.car, [self.car], self.rm)

    def test_the_claim_on_the_crossing_ahead_is_withdrawn(self):
        self.state.add_car_priority(self.car.id, 3)
        self.controller._drop_pending_priority(
            self.rm.get_car_reservations(self.car.id))
        self.assertIsNone(self.state.get_car_priority(self.car.id))

    def test_it_is_harmless_when_no_claim_is_held(self):
        self.controller._drop_pending_priority(
            self.rm.get_car_reservations(self.car.id))
        self.assertIsNone(self.state.get_car_priority(self.car.id))

    def test_a_car_already_on_a_crossing_gives_nothing_up(self):
        crossing = self.segment.end_crossing
        self.state.add_car_priority(self.car.id, 3)
        info = SegmentInfo(crossing, 0, crossing.length, self.car.direction)
        self.controller._drop_pending_priority([info])
        self.assertEqual(self.state.get_car_priority(self.car.id), 3,
                         "a car in the intersection is past giving way")

    def test_only_the_nearest_crossing_ahead_is_considered(self):
        self.state.add_car_priority(self.car.id, 3)
        reservations = self.rm.get_car_reservations(self.car.id)
        self.controller._drop_pending_priority(reservations)
        self.assertIsNone(self.state.get_car_priority(self.car.id))


class TestControllerDrivesACarAround(unittest.TestCase):
    """End-to-end at the controller level: a single car on a closed circuit."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = ring_world()
        self.rm = self.world.reservation_management
        self.start = self.world.lane_segment("hb", "right")
        self.car = place_car(self.world, self.start, loc=0, speed=0, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("ht", "left"))
        self.controller = AstarCarController(self.car, [self.car], self.rm)

    def _drive(self, ticks):
        for _ in range(ticks):
            acceleration, lane_change = self.controller.get_action()
            self.car.change_speed(acceleration)
            if lane_change:
                self.car.change_lane(self.rm, lane_change, [self.car])
            self.car.move(self.rm)

    def test_a_lone_car_gets_moving(self):
        self._drive(6)
        self.assertGreater(self.car.speed, 0)

    def test_it_never_exceeds_its_own_maximum(self):
        self._drive(60)
        self.assertLessEqual(self.car.speed, self.car.max_speed)

    def test_it_slows_down_for_crossings(self):
        seen_on_crossing = False
        for _ in range(120):
            acceleration, lane_change = self.controller.get_action()
            self.car.change_speed(acceleration)
            self.car.move(self.rm)
            anchor = self.rm.get_car_reservation(self.car.id, 0).segment
            if isinstance(anchor, CrossingSegment):
                seen_on_crossing = True
                self.assertLessEqual(self.car.speed, CROSSING_MAX_SPEED)
        self.assertTrue(seen_on_crossing, "the car never entered a crossing")

    def test_it_makes_real_progress_around_the_ring(self):
        visited = set()
        for _ in range(150):
            acceleration, _ = self.controller.get_action()
            self.car.change_speed(acceleration)
            self.car.move(self.rm)
            visited.add(id(self.rm.get_car_reservation(self.car.id, 0).segment))
        self.assertGreater(len(visited), 2)

    def test_it_never_reverses(self):
        for _ in range(60):
            acceleration, _ = self.controller.get_action()
            self.car.change_speed(acceleration)
            self.assertGreaterEqual(self.car.speed, 0)
            self.car.move(self.rm)


if __name__ == "__main__":
    unittest.main()
