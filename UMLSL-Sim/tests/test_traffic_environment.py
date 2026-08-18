"""Functional tests for `simulation.traffic_environment` -- the tick.

`TrafficEnv` is the seam every front end and every learner is written against:
build a world, collect one action per car, apply them, then decide whether the
episode is over. These tests drive it through a scripted controller rather than
the A* one, so what is under test is the environment's tick and not the NPC
policy's taste -- the controllers get their own file.
"""

import random
import unittest

from umlsl_sim.config.simulation_constants import DEADLOCK_FRAMES, WINNING_SCORE
from umlsl_sim.factories.car_spec import CarSpec, PositionRef
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.road_network.road_network import Direction, LaneSegment, Road
from umlsl_sim.simulation.traffic_environment import CarState, TrafficEnv

from tests.helpers import constant_controller_factory


def _roads():
    """A fresh single-crossing network. `TrafficEnv` builds the segments itself."""
    return [Road("h1", True, 200, 1, 1), Road("v1", False, 200, 1, 1)]


def _wide_roads():
    """A network with room for a handful of cars."""
    return [Road("h1", True, 200, 2, 2), Road("v1", False, 200, 2, 2)]


def _env(players=1, **kwargs):
    random.seed(4242)
    Car.reset_id_counter()
    kwargs.setdefault("npc_controller_factory", constant_controller_factory((0, 0)))
    return TrafficEnv(roads=kwargs.pop("roads", _roads()), players=players, **kwargs)


class TestConstruction(unittest.TestCase):

    def test_the_segment_graph_is_built_from_the_roads(self):
        env = _env(players=1)
        self.assertTrue(env.segments)
        self.assertTrue(env.intersections)

    def test_the_requested_number_of_npcs_is_spawned(self):
        env = _env(players=3, roads=_wide_roads())
        self.assertEqual(len(env.npc_cars), 3)
        self.assertEqual(len(env.cars), 3)

    def test_every_npc_gets_a_controller(self):
        env = _env(players=3, roads=_wide_roads())
        self.assertEqual(len(env.controllers), len(env.npc_cars))

    def test_an_agent_car_is_spawned_on_request(self):
        env = _env(players=2, roads=_wide_roads(), with_agent=True)
        self.assertIsNotNone(env.agent_car)
        self.assertIs(env.agent_car.type, CarType.AGENT)
        self.assertIn(env.agent_car, env.cars)
        self.assertNotIn(env.agent_car, env.npc_cars)

    def test_the_agent_car_gets_no_controller(self):
        env = _env(players=2, roads=_wide_roads(), with_agent=True)
        self.assertEqual(len(env.controllers), len(env.npc_cars))

    def test_without_an_agent_there_is_no_agent_car(self):
        env = _env(players=1)
        self.assertIsNone(env.agent_car)

    def test_the_clock_and_counters_start_at_zero(self):
        env = _env(players=1)
        self.assertEqual(env.time, 0)
        self.assertEqual(env.stalled_frames, 0)
        self.assertEqual(env.total_crashes, 0)
        self.assertEqual(set(env.crashes), set(Direction))

    def test_the_default_controller_is_the_astar_one(self):
        random.seed(1)
        Car.reset_id_counter()
        env = TrafficEnv(roads=_roads(), players=1)
        from umlsl_sim.control.astar.astar_car_controller import AstarCarController
        self.assertIsInstance(env.controllers[0], AstarCarController)

    def test_a_custom_controller_factory_is_used_instead(self):
        env = _env(players=1)
        from tests.helpers import RecordingController
        self.assertIsInstance(env.controllers[0], RecordingController)

    def test_the_history_is_primed_with_the_cars_and_the_map(self):
        env = _env(players=2, roads=_wide_roads())
        self.assertEqual(len(env.game_history.list_of_cars), len(env.cars))
        self.assertEqual(len(env.game_history.map), len(env.roads))
        self.assertEqual(len(env.game_history.car_snapshots), len(env.cars),
                         "the history must be able to replay this episode")


class TestConstructionValidation(unittest.TestCase):

    def test_more_cars_than_lane_segments_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            _env(players=99)
        self.assertIn("lane segments", str(ctx.exception))

    def test_the_error_says_how_many_cars_would_fit(self):
        with self.assertRaises(ValueError) as ctx:
            _env(players=99)
        self.assertIn("Lower `players`", str(ctx.exception))

    def test_the_agent_counts_towards_the_capacity(self):
        capacity = len([s for s in TrafficEnv(
            roads=_roads(), players=1,
            npc_controller_factory=constant_controller_factory()).segments
            if isinstance(s, LaneSegment)])
        with self.assertRaises(ValueError):
            _env(players=capacity, with_agent=True)

    def test_two_predefined_agents_are_refused(self):
        specs = [CarSpec(type=CarType.AGENT), CarSpec(type=CarType.AGENT)]
        with self.assertRaises(ValueError) as ctx:
            _env(players=1, predefined_cars=specs, with_agent=True)
        self.assertIn("At most one predefined car of type AGENT", str(ctx.exception))

    def test_a_predefined_agent_without_with_agent_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            _env(players=1, predefined_cars=[CarSpec(type=CarType.AGENT)])
        self.assertIn("with_agent=True", str(ctx.exception))

    def test_more_predefined_npcs_than_players_is_refused(self):
        specs = [CarSpec(), CarSpec(), CarSpec()]
        with self.assertRaises(ValueError) as ctx:
            _env(players=2, predefined_cars=specs, roads=_wide_roads())
        self.assertIn("reduce predefined NPCs or raise players", str(ctx.exception))


class TestPredefinedCars(unittest.TestCase):

    def test_a_predefined_npc_is_placed_where_the_spec_says(self):
        spec = CarSpec(start=PositionRef("h1", "right", 0, 120), speed=3, name="Pinned")
        env = _env(players=1, predefined_cars=[spec])
        car = env.npc_cars[0]
        self.assertEqual(car.name, "Pinned")
        self.assertEqual(car.speed, 3)

    def test_random_npcs_top_the_count_up_to_players(self):
        spec = CarSpec(start=PositionRef("h1", "right", 0, 120), name="Pinned")
        env = _env(players=3, predefined_cars=[spec], roads=_wide_roads())
        self.assertEqual(len(env.npc_cars), 3)
        self.assertEqual(sum(1 for c in env.npc_cars if c.name == "Pinned"), 1)

    def test_a_predefined_agent_replaces_the_random_one(self):
        spec = CarSpec(type=CarType.AGENT,
                       start=PositionRef("h1", "right", 0, 40), name="Hero")
        env = _env(players=1, predefined_cars=[spec], with_agent=True)
        self.assertEqual(env.agent_car.name, "Hero")

    def test_the_agent_is_created_before_the_npcs(self):
        env = _env(players=2, roads=_wide_roads(), with_agent=True)
        self.assertIs(env.cars[0], env.agent_car)

    def test_the_spec_list_is_copied(self):
        specs = [CarSpec(start=PositionRef("h1", "right", 0, 120))]
        env = _env(players=1, predefined_cars=specs)
        specs.clear()
        self.assertEqual(len(env.predefined_cars), 1)


class TestReset(unittest.TestCase):

    def setUp(self):
        self.env = _env(players=2, roads=_wide_roads(), with_agent=True)

    def test_reset_rebuilds_every_car(self):
        before = list(self.env.cars)
        self.env.reset()
        for car in self.env.cars:
            self.assertNotIn(car, before)

    def test_reset_restores_the_car_counts(self):
        self.env.reset()
        self.assertEqual(len(self.env.npc_cars), 2)
        self.assertIsNotNone(self.env.agent_car)
        self.assertEqual(len(self.env.controllers), 2)

    def test_reset_rewinds_the_clock_and_the_counters(self):
        self.env.play_step(action=(0, 0))
        self.env.reset()
        self.assertEqual(self.env.time, 0)
        self.assertEqual(self.env.stalled_frames, 0)
        self.assertEqual(self.env.total_crashes, 0)
        self.assertEqual(sum(self.env.crashes.values()), 0)

    def test_reset_clears_the_reservation_book_of_the_old_cars(self):
        old = list(self.env.cars)
        self.env.reset()
        for car in old:
            with self.assertRaises(KeyError):
                self.env.reservation_management.get_car_reservations(car.id)

    def test_reset_clears_every_intersection_claim(self):
        for _ in range(20):
            self.env.play_step(action=(0, 0))
        self.env.reset()
        for intersection in self.env.intersections:
            self.assertEqual(intersection.intersection_state.get_priority_items(), [])

    def test_reset_clears_every_crossing_departure_time(self):
        for _ in range(20):
            self.env.play_step(action=(0, 0))
        self.env.reset()
        for intersection in self.env.intersections:
            for segment in intersection.segments:
                for car in self.env.cars:
                    self.assertIsNone(
                        segment.crossing_segment_state.get_time_to_leave(car.id))

    def test_reset_starts_a_fresh_recording(self):
        self.env.play_step(action=(0, 0))
        self.env.reset()
        self.assertEqual(self.env.game_history.action_length, 0)

    def test_reset_does_not_rebuild_the_road_network(self):
        segments = self.env.segments
        self.env.reset()
        self.assertIs(self.env.segments, segments)


class TestPlayStep(unittest.TestCase):

    def setUp(self):
        self.env = _env(players=2, roads=_wide_roads())

    def test_a_quiet_step_reports_no_outcome(self):
        self.assertIsNone(self.env.play_step())

    def test_the_environment_clock_advances_once_per_step(self):
        """FIXED (FINDINGS #9): `self.time += 1` used to sit in `_execute_action`.

        That runs once per living car, so an environment with three cars
        advanced its clock three times per tick -- three times faster than the
        `Car.time` the crossing time-to-leave arithmetic is written against.
        """
        self.env.play_step()
        self.assertEqual(self.env.time, 1)
        self.env.play_step()
        self.assertEqual(self.env.time, 2)

    def test_the_environment_clock_keeps_step_with_the_cars(self):
        for _ in range(5):
            self.env.play_step()
        for car in self.env.cars:
            self.assertEqual(car.time, self.env.time)

    def test_every_car_acts_once_per_step(self):
        self.env.play_step()
        for car in self.env.cars:
            self.assertEqual(car.time, 1)

    def test_each_action_is_recorded_in_the_history(self):
        self.env.play_step()
        self.assertEqual(self.env.game_history.action_length, len(self.env.cars))

    def test_the_controllers_are_shuffled_each_step(self):
        """Action order is randomised so no car has a permanent advantage."""
        env = _env(players=4, roads=_wide_roads())
        orders = set()
        for _ in range(20):
            env.play_step()
            orders.add(tuple(id(c) for c in env.controllers))
        self.assertGreater(len(orders), 1)

    def test_an_agent_action_is_applied_and_recorded(self):
        env = _env(players=1, roads=_wide_roads(), with_agent=True)
        before = env.agent_car.speed
        env.play_step(action=(3, 0))
        self.assertEqual(env.agent_car.speed, min(before + 3, env.agent_car.max_speed))

    def test_an_agent_env_stepped_without_an_action_leaves_the_agent_alone(self):
        env = _env(players=1, roads=_wide_roads(), with_agent=True)
        before = (env.agent_car.loc, env.agent_car.time)
        env.play_step()
        self.assertEqual((env.agent_car.loc, env.agent_car.time), before)

    def test_a_dead_agent_is_not_stepped(self):
        env = _env(players=1, roads=_wide_roads(), with_agent=True)
        env.agent_car.handle_car_death(env.reservation_management)
        env.play_step(action=(5, 0))
        self.assertEqual(env.agent_car.speed, 0)

    def test_a_world_with_no_cars_is_immediately_over(self):
        """`all([])` is vacuously true, so an empty world reports game over --
        which is the right answer, if an unusual way to reach it."""
        env = _env(players=0)
        self.assertEqual(env.play_step(), "game_over")


class TestStallAndDeadlock(unittest.TestCase):

    def setUp(self):
        self.env = _env(players=2, roads=_wide_roads())

    def test_moving_traffic_never_stalls(self):
        for car in self.env.cars:
            car.speed = 5
        for _ in range(DEADLOCK_FRAMES + 3):
            outcome = self.env.play_step()
            self.assertNotEqual(outcome, "deadlock")

    def test_standing_traffic_accumulates_stalled_frames(self):
        for car in self.env.cars:
            car.speed = 0
        self.env.play_step()
        self.assertEqual(self.env.stalled_frames, 1)

    def test_a_stall_that_outlasts_the_window_is_a_deadlock(self):
        for car in self.env.cars:
            car.speed = 0
        outcome = None
        for _ in range(DEADLOCK_FRAMES):
            outcome = self.env.play_step()
        self.assertEqual(outcome, "deadlock")

    def test_one_car_moving_resets_the_count(self):
        for car in self.env.cars:
            car.speed = 0
        self.env.play_step()
        self.env.cars[0].speed = 5
        self.env.play_step()
        self.assertEqual(self.env.stalled_frames, 0)

    def test_a_wreck_left_at_speed_does_not_suppress_deadlock_detection(self):
        wreck, living = self.env.cars
        wreck.handle_car_death(self.env.reservation_management)
        wreck.speed = 9        # a wreck can be left parked at a non-zero speed
        living.speed = 0
        self.env.play_step()
        self.assertEqual(self.env.stalled_frames, 1,
                         "only living cars have a say in whether traffic stalled")

    def test_a_world_of_wrecks_is_over_rather_than_deadlocked(self):
        for car in self.env.cars:
            car.handle_car_death(self.env.reservation_management)
        self.assertEqual(self.env.play_step(), "game_over")


class TestCollisionHandling(unittest.TestCase):

    def setUp(self):
        random.seed(11)
        Car.reset_id_counter()
        specs = [
            CarSpec(start=PositionRef("h1", "right", 0, 0), speed=0, size=40,
                    name="Rear"),
            CarSpec(start=PositionRef("h1", "right", 0, 60), speed=0, size=40,
                    name="Front"),
        ]
        self.env = TrafficEnv(
            roads=_wide_roads(), players=2, predefined_cars=specs,
            npc_controller_factory=constant_controller_factory((0, 0)))
        self.rear = next(c for c in self.env.cars if c.name == "Rear")
        self.front = next(c for c in self.env.cars if c.name == "Front")

    def test_driving_into_the_car_ahead_kills_both(self):
        self.rear.speed = 20
        for _ in range(4):
            self.env.play_step()
            if self.rear.get_death_status():
                break
        self.assertTrue(self.rear.get_death_status())
        self.assertTrue(self.front.get_death_status())

    def test_a_crash_is_counted(self):
        self.rear.speed = 20
        for _ in range(4):
            self.env.play_step()
            if self.env.total_crashes:
                break
        self.assertEqual(self.env.total_crashes, 1)

    def test_a_crash_is_attributed_to_a_direction(self):
        self.rear.speed = 20
        for _ in range(4):
            self.env.play_step()
            if self.env.total_crashes:
                break
        self.assertEqual(sum(self.env.crashes.values()), self.env.total_crashes)


class TestIllegalMoves(unittest.TestCase):

    def test_an_npc_that_attempts_an_impossible_lane_change_dies(self):
        env = _env(players=1, npc_controller_factory=constant_controller_factory((0, 1)))
        for _ in range(3):
            env.play_step()
            if env.npc_cars[0].get_death_status():
                break
        self.assertTrue(env.npc_cars[0].get_death_status(),
                        "the single-lane road offers no adjacent lane")

    def test_the_agent_is_flagged_rather_than_killed(self):
        env = _env(players=1, roads=_roads(), with_agent=True)
        env.play_step(action=(0, 1))
        self.assertFalse(env.agent_car.get_death_status())
        self.assertTrue(env.agent_car.illegal_move)


class TestGoalsAndScoring(unittest.TestCase):

    def setUp(self):
        self.env = _env(players=1, roads=_wide_roads())
        self.car = self.env.npc_cars[0]

    def test_reaching_a_goal_scores_and_promotes_the_second_one(self):
        from umlsl_sim.simulation.road_network.road_network import Goal
        centre = self.car.get_center(self.env.reservation_management)
        anchor = self.env.reservation_management.get_car_reservation(self.car.id, 0)
        self.car.goal = Goal(anchor.segment, self.car.color)
        self.car.goal.pos.x, self.car.goal.pos.y = centre[0], centre[1]
        promoted = self.car.second_goal

        self.car.speed = 0
        self.env.play_step()

        self.assertEqual(self.car.score, 1)
        self.assertIs(self.car.goal, promoted)

    def test_a_replacement_second_goal_is_placed(self):
        from umlsl_sim.simulation.road_network.road_network import Goal
        centre = self.car.get_center(self.env.reservation_management)
        anchor = self.env.reservation_management.get_car_reservation(self.car.id, 0)
        self.car.goal = Goal(anchor.segment, self.car.color)
        self.car.goal.pos.x, self.car.goal.pos.y = centre[0], centre[1]
        old_second = self.car.second_goal

        self.car.speed = 0
        self.env.play_step()

        self.assertIsNot(self.car.second_goal, old_second)

    def test_passing_the_winning_score_ends_the_episode(self):
        self.car.score = WINNING_SCORE + 1
        self.assertEqual(self.env.play_step(), "game_over")

    def test_the_winning_score_itself_is_not_yet_a_win(self):
        self.car.score = WINNING_SCORE
        self.assertIsNone(self.env.play_step())


class TestCarStates(unittest.TestCase):

    def setUp(self):
        self.env = _env(players=2, roads=_wide_roads(), with_agent=True)

    def test_a_snapshot_is_taken_of_every_car(self):
        states = self.env.car_states()
        self.assertEqual(len(states), len(self.env.cars))
        self.assertTrue(all(isinstance(s, CarState) for s in states))

    def test_a_snapshot_records_identity_score_and_death(self):
        self.env.cars[0].score = 7
        self.env.cars[1].handle_car_death(self.env.reservation_management)
        states = self.env.car_states()
        self.assertEqual(states[0].score, 7)
        self.assertTrue(states[1].dead)
        self.assertEqual(states[0].name, self.env.cars[0].name)
        self.assertIs(states[0].type, self.env.cars[0].type)

    def test_a_snapshot_survives_a_reset(self):
        self.env.cars[0].score = 5
        states = self.env.car_states()
        self.env.reset()
        self.assertEqual(states[0].score, 5)

    def test_a_snapshot_is_immutable(self):
        state = self.env.car_states()[0]
        with self.assertRaises(Exception):
            state.score = 99

    def test_current_state_prints_the_live_world_by_default(self):
        # Smoke: it writes to stdout and returns nothing.
        self.assertIsNone(self.env.current_state())

    def test_current_state_accepts_a_snapshot(self):
        states = self.env.car_states()
        self.env.reset()
        self.assertIsNone(self.env.current_state(states))


class TestMovedFlag(unittest.TestCase):
    """`TrafficEnv.moved` -- FINDINGS #12: written, never read.

    It is set to True in `__init__` and again in `reset`, and nothing anywhere
    in the package reads it. Pinned so its removal is a deliberate act.
    """

    def test_it_is_true_after_construction_and_after_a_reset(self):
        env = _env(players=1)
        self.assertTrue(env.moved)
        env.reset()
        self.assertTrue(env.moved)

    def test_stepping_never_changes_it(self):
        env = _env(players=1)
        for _ in range(5):
            env.play_step()
        self.assertTrue(env.moved)


if __name__ == "__main__":
    unittest.main()
