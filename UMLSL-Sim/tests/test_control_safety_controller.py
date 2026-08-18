"""Tests for `control.safety.safety_controller` -- what is safe, not what is best.

`SafetyController` shares its machinery with `AstarCarController` but answers a
different question: instead of "the action to take" it reports the ceiling on
acceleration and which lane changes are available. Those two answers are what
`ActionShield` turns into a Gymnasium mask, so the properties the shield's
soundness argument rests on -- monotonicity, and "stay" always being safe -- are
asserted here rather than left implicit.
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
    RIGHT_LANE_CHANGE,
)
from umlsl_sim.control.safety.safety_controller import SafetyController
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    LaneSegment,
    SegmentInfo,
)

from tests.helpers import place_car, ring_world, single_crossing_world, two_lane_world


class _SafetyFixture(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.cars = [self.car]
        self.controller = SafetyController(self.car, self.cars, self.rm)

    def reservations(self):
        return self.rm.get_car_reservations(self.car.id)

    def max_acc(self):
        if self.controller.first_go:
            self.controller.get_max_acceleration()
        return self.controller.get_max_acceleration()


class TestGetMaxAcceleration(_SafetyFixture):

    def test_the_first_call_is_a_no_op(self):
        self.assertEqual(self.controller.get_max_acceleration(), 0)

    def test_an_empty_road_permits_full_acceleration(self):
        self.assertEqual(self.max_acc(), MAX_ACC)

    def test_the_answer_is_within_the_action_range(self):
        value = self.max_acc()
        self.assertGreaterEqual(value, -MAX_DEC)
        self.assertLessEqual(value, MAX_ACC)

    def test_asking_does_not_move_the_car(self):
        before = (self.car.loc, self.car.speed, self.car.time)
        self.max_acc()
        self.assertEqual((self.car.loc, self.car.speed, self.car.time), before)

    def test_it_returns_a_bare_acceleration_rather_than_an_action_pair(self):
        self.assertIsInstance(self.max_acc(), int)

    def test_a_stationary_car_is_never_told_to_reverse(self):
        self.car.speed = 0
        self.assertGreaterEqual(self.max_acc(), 0)

    def test_a_car_at_its_maximum_is_not_told_to_speed_up(self):
        self.car.speed = self.car.max_speed
        self.assertLessEqual(self.max_acc(), 0)

    def test_a_lane_change_in_progress_is_also_checked_against_the_target_lane(self):
        world = two_lane_world()
        rm = world.reservation_management
        inner = world.lane_segment("h1", "right", num=0)
        outer = world.lane_segment("h1", "right", num=1)
        car = place_car(world, inner, loc=0, speed=10, size=40,
                        max_speed=LANE_MAX_SPEED)
        blocker = place_car(world, outer, loc=70, speed=0, size=40,
                            max_speed=LANE_MAX_SPEED, name="Beside")
        controller = SafetyController(car, [car, blocker], rm)
        controller.get_max_acceleration()

        free = controller.get_max_acceleration()
        car.changing_lane = True
        rm.set_reserved_lane_change_segment(car.id, (car.time, outer))
        self.assertLessEqual(controller.get_max_acceleration(), free)

    def test_a_car_marked_as_changing_lane_with_no_registration_is_an_error(self):
        self.controller.get_max_acceleration()
        self.car.changing_lane = True
        with self.assertRaises(RuntimeError) as ctx:
            self.controller.get_max_acceleration()
        self.assertIn("no reserved", str(ctx.exception))


class TestGetMaxAccelerationWithTraffic(unittest.TestCase):

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.blocker = place_car(self.world, self.segment, loc=90, speed=0, size=40,
                                 max_speed=LANE_MAX_SPEED, name="Block")
        self.controller = SafetyController(self.car, [self.car, self.blocker], self.rm)
        self.controller.get_max_acceleration()

    def test_a_stopped_leader_lowers_the_ceiling(self):
        self.assertLess(self.controller.get_max_acceleration(), MAX_ACC)

    def test_a_leader_right_in_front_forces_full_braking(self):
        self.blocker.loc = self.car.loc + self.car.size
        self.rm.update_car_reservation_begin(self.blocker.id, 0, self.blocker.loc)
        self.assertEqual(self.controller.get_max_acceleration(),
                         -min(MAX_DEC, self.car.speed))

    def test_the_ceiling_is_a_ceiling_and_not_a_target(self):
        """Every acceleration at or below the answer must also be safe -- this
        is what lets the shield mask a whole prefix of the action space."""
        ceiling = self.controller.get_max_acceleration()
        reservations = self.rm.get_car_reservations(self.car.id)
        for acceleration in range(-min(MAX_DEC, self.car.speed), ceiling + 1):
            projected = self.controller._project_reservation(
                reservations, self.car.speed + acceleration)
            self.assertIsNotNone(projected, f"no projection at {acceleration}")
            unsafe, _ = self.controller._violates_safety(
                reservations, projected, self.car.speed + acceleration)
            self.assertFalse(unsafe, f"acceleration {acceleration} was not safe")


class TestGetSafeLaneChange(unittest.TestCase):

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
        self.controller = SafetyController(self.car, self.cars, self.rm)
        self.controller.get_max_acceleration()

    def _verdict(self, current_acc=0):
        return self.controller.get_safe_lane_change(
            self.rm.get_car_reservations(self.car.id), current_acc)

    def test_the_verdict_is_a_triple_in_right_stay_left_order(self):
        verdict = self._verdict()
        self.assertEqual(len(verdict), 3)
        self.assertTrue(all(isinstance(v, bool) for v in verdict))

    def test_staying_in_lane_is_always_safe(self):
        self.assertTrue(self._verdict()[1 + 0])

    def test_a_free_neighbouring_lane_is_offered(self):
        self.assertTrue(self._verdict()[1 + LEFT_LANE_CHANGE])

    def test_a_lane_that_is_not_there_is_not_offered(self):
        self.assertFalse(self._verdict()[1 + RIGHT_LANE_CHANGE])

    def test_an_occupied_neighbouring_lane_is_not_offered(self):
        blocker = place_car(self.world, self.outer, loc=0, speed=0, size=40,
                            max_speed=LANE_MAX_SPEED, name="Beside")
        self.cars.append(blocker)
        self.assertFalse(self._verdict()[1 + LEFT_LANE_CHANGE])

    def test_staying_is_still_offered_when_both_sides_are_blocked(self):
        blocker = place_car(self.world, self.outer, loc=0, speed=0, size=40,
                            max_speed=LANE_MAX_SPEED, name="Beside")
        self.cars.append(blocker)
        self.assertEqual(self._verdict(), [False, True, False])

    def test_too_little_room_to_complete_the_change_offers_only_staying(self):
        self.car.loc = self.inner.length - 5
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.inner.length)
        self.assertEqual(self._verdict(current_acc=MAX_ACC), [False, True, False])

    def test_a_car_straddling_a_crossing_may_only_stay(self):
        world = single_crossing_world()
        rm = world.reservation_management
        car = place_car(world, world.lane_segment("h1", "right"), speed=10, size=40,
                        max_speed=LANE_MAX_SPEED,
                        goal_segment=world.lane_segment("v1", "right"))
        controller = SafetyController(car, [car], rm)
        for _ in range(14):
            car.move(rm)
        reservations = rm.get_car_reservations(car.id)
        self.assertGreater(len(reservations), 1)
        self.assertEqual(controller.get_safe_lane_change(reservations, 0),
                         [False, True, False])

    def test_the_feasibility_test_is_monotone_in_acceleration(self):
        """The shield evaluates lane changes at the *largest* admitted
        acceleration and relies on the verdict holding for every smaller one."""
        self.car.loc = self.inner.length // 2
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.car.loc + 70)
        verdicts = [self._verdict(current_acc=a) for a in range(-MAX_DEC, MAX_ACC + 1)]
        for lane in range(3):
            column = [v[lane] for v in verdicts]
            # once False it must stay False as the acceleration grows
            self.assertEqual(column, sorted(column, reverse=True),
                             f"lane index {lane} is not monotone")


class TestSafetyControllerInternals(unittest.TestCase):
    """`_project_reservation` and `_violates_safety`, the shared machinery."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.segment = self.world.lane_segment("h1", "right")
        self.car = place_car(self.world, self.segment, loc=0, speed=10, size=40,
                             max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("v1", "right"))
        self.controller = SafetyController(self.car, [self.car], self.rm)

    def test_a_projection_never_shrinks_below_the_body_and_buffer(self):
        projected = self.controller._project_reservation(
            self.rm.get_car_reservations(self.car.id), 0)
        self.assertGreaterEqual(abs(projected[-1].end) - abs(projected[-1].begin),
                                self.car.size + BUFFER)

    def test_a_faster_projection_reaches_further(self):
        reservations = self.rm.get_car_reservations(self.car.id)
        reach = []
        for speed in (0, 5, 10, LANE_MAX_SPEED):
            projected = self.controller._project_reservation(reservations, speed)
            reach.append(sum(abs(s.end - s.begin) for s in projected))
        self.assertEqual(reach, sorted(reach))

    def test_an_empty_road_violates_nothing(self):
        reservations = self.rm.get_car_reservations(self.car.id)
        projected = self.controller._project_reservation(reservations, 10)
        self.assertEqual(self.controller._violates_safety(reservations, projected, 10),
                         (False, False))

    def test_being_outranked_at_a_new_crossing_is_a_priority_block(self):
        self.car.loc = self.segment.length - 30
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        reservations = self.rm.get_car_reservations(self.car.id)
        projected = self.controller._project_reservation(reservations, LANE_MAX_SPEED)
        if projected is None or not any(isinstance(s.segment, CrossingSegment)
                                        for s in projected):
            self.skipTest("the projection never reached a crossing")
        state = self.segment.end_crossing.intersection.intersection_state
        state.add_car_priority(self.car.id, 10)
        state.add_car_priority("rival", 1)
        self.assertEqual(
            self.controller._violates_safety(reservations, projected, LANE_MAX_SPEED),
            (True, True))

    def test_the_priority_flag_is_cleared_on_every_call(self):
        self.controller._last_call_priority_blocked = True
        self.controller.get_accelerate(
            self.rm.get_car_reservations(self.car.id), True)
        self.assertFalse(self.controller._last_call_priority_blocked)

    def test_no_known_route_gives_no_projection(self):
        from umlsl_sim.simulation.road_network.road_network import Goal
        elsewhere = single_crossing_world().lane_segment("h1", "right")
        self.car.goal = Goal(elsewhere, (0, 0, 0))
        self.car.second_goal = Goal(elsewhere, (0, 0, 0))
        self.car.loc = self.segment.length - 5
        self.rm.update_car_reservation_begin(self.car.id, 0, self.car.loc)
        self.rm.update_car_reservation_end(self.car.id, 0, self.segment.length)
        self.assertIsNone(self.controller._project_reservation(
            self.rm.get_car_reservations(self.car.id), LANE_MAX_SPEED))


class TestSafetyControllerAgreesWithAstar(unittest.TestCase):
    """The two controllers share `get_accelerate`, so they must agree on it.

    `AstarCarController` picks an action; `SafetyController` reports the
    ceiling. On the same state the ceiling must be exactly the acceleration the
    A* controller chose, or the shield would be masking a different rule from
    the one the NPCs drive by.
    """

    def setUp(self):
        Car.reset_id_counter()
        self.world = ring_world()
        self.rm = self.world.reservation_management
        self.car = place_car(self.world, self.world.lane_segment("hb", "right"),
                             loc=0, speed=5, size=40, max_speed=LANE_MAX_SPEED,
                             goal_segment=self.world.lane_segment("ht", "left"))

    def test_the_ceiling_matches_the_chosen_acceleration_over_a_whole_run(self):
        from umlsl_sim.control.astar.astar_car_controller import AstarCarController

        astar = AstarCarController(self.car, [self.car], self.rm)
        safety = SafetyController(self.car, [self.car], self.rm)
        astar.get_action()
        safety.get_max_acceleration()

        for _ in range(60):
            chosen, _ = astar.get_action()
            ceiling = safety.get_max_acceleration()
            self.assertEqual(chosen, ceiling)
            self.car.change_speed(chosen)
            self.car.move(self.rm)


if __name__ == "__main__":
    unittest.main()
