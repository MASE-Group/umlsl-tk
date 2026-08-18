"""Integration: full episodes on the bundled scenarios, driven by the real A*.

Everything below runs the whole stack -- scenario parser, factories, segment
builder, reservation book, A* controller, tick -- and asserts the properties the
simulator exists to provide rather than any one function's return value:

* nothing ever crashes (the safety rules are collision-free, not merely careful);
* traffic keeps moving (the crossing-claim lease breaks every cyclic wait);
* the reservation book stays consistent with the cars it describes.

These are the tests that fail when a change is locally reasonable and globally
wrong, which is exactly what the unit tests cannot see.
"""

import random
import unittest

from umlsl_sim.config.simulation_constants import DEADLOCK_FRAMES
from umlsl_sim.scenario.loader import available_scenarios, load_scenario
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.event_checks import collision_check
from umlsl_sim.simulation.road_network.road_network import CrossingSegment, LaneSegment
from umlsl_sim.simulation.traffic_environment import TrafficEnv

#: Kept small enough that the whole file stays well under a second per scenario.
EPISODE_STEPS = 120
MAX_PLAYERS = 8


def build(scenario_key, seed, players=None, with_agent=False):
    random.seed(seed)
    Car.reset_id_counter()
    scenario = load_scenario(scenario_key)
    return TrafficEnv(
        roads=scenario["roads"],
        players=players if players is not None else min(scenario["players"], MAX_PLAYERS),
        predefined_cars=scenario["predefined_cars"],
        with_agent=with_agent,
    )


def run(env, steps=EPISODE_STEPS, action=(0, 0)):
    """Step an episode, returning (outcome, steps_taken)."""
    for taken in range(1, steps + 1):
        outcome = env.play_step(action=action if env.agent else None)
        if outcome is not None:
            return outcome, taken
    return None, steps


def assert_book_is_consistent(case, env):
    """Every reservation is mirrored in the occupancy table, and vice versa."""
    rm = env.reservation_management
    for car in env.cars:
        for info in rm.get_car_reservations(car.id):
            case.assertIn(car.id, rm.get_cars_on_segment(info.segment),
                          f"{car.id} reserves {info.segment} but is not on it")

    for segment in env.segments:
        for car_id in rm.get_cars_on_segment(segment):
            held = [i.segment for i in rm.get_car_reservations(car_id)]
            case.assertIn(segment, held,
                          f"{car_id} occupies {segment} without reserving it")


def assert_nobody_has_collided(case, env):
    for i, first in enumerate(env.cars):
        for second in env.cars[i + 1:]:
            case.assertFalse(
                collision_check(first, second, env.reservation_management),
                f"{first.name} overlaps {second.name}")


class TestEveryScenarioRuns(unittest.TestCase):
    """The headline property, over every scenario the package ships."""

    def test_every_bundled_scenario_loads_and_builds(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                self.assertTrue(env.cars)
                self.assertTrue(env.segments)

    def test_no_scenario_ever_produces_a_collision(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                run(env)
                self.assertEqual(env.total_crashes, 0)
                assert_nobody_has_collided(self, env)

    def test_no_scenario_deadlocks(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                outcome, _ = run(env)
                self.assertNotEqual(outcome, "deadlock")

    def test_no_car_dies(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                run(env)
                for car in env.cars:
                    self.assertFalse(car.get_death_status(), car.name)

    def test_every_car_gets_moving(self):
        """Nothing is permanently frozen: every car reaches a positive speed.

        Segment traversal is the wrong per-car measure -- `one_road` has lane
        segments hundreds of units long, so a car can cruise the whole episode
        without ever crossing a boundary -- and goal-scoring is wrong for the
        two- and three-car scenarios, where a goal is simply further away than
        EPISODE_STEPS of driving.
        """
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                moved = {car.id: car.speed > 0 for car in env.cars}
                for _ in range(EPISODE_STEPS):
                    env.play_step()
                    for car in env.cars:
                        moved[car.id] = moved[car.id] or car.speed > 0
                for car in env.cars:
                    self.assertTrue(moved[car.id], f"{car.name} never moved at all")

    def test_the_fleet_traverses_segments(self):
        """Traffic goes somewhere: cars cross segment boundaries, so the
        crossing and hand-over machinery is genuinely being exercised."""
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                anchors = {car.id: {id(env.reservation_management
                                       .get_car_reservation(car.id, 0).segment)}
                           for car in env.cars}
                for _ in range(EPISODE_STEPS):
                    env.play_step()
                    for car in env.cars:
                        anchors[car.id].add(id(env.reservation_management
                                               .get_car_reservation(car.id, 0).segment))
                traversals = sum(len(seen) - 1 for seen in anchors.values())
                self.assertGreater(traversals, 0,
                                   "no car anywhere left the segment it started on")

    def test_busy_scenarios_score_goals(self):
        """Where there is enough traffic and enough road, cars reach goals."""
        for key in ("one_crossing", "two_crossings", "horizontal_vertical",
                    "big_scenario", "starting_scenario"):
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                run(env)
                self.assertGreater(sum(car.score for car in env.cars), 0,
                                   "no car reached a single goal in the episode")

    def test_the_reservation_book_stays_consistent(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                env = build(key, seed=1)
                run(env)
                assert_book_is_consistent(self, env)


class TestCollisionFreedomAcrossSeeds(unittest.TestCase):
    """Different seeds place different traffic; none of it may crash."""

    SCENARIOS = ("one_crossing", "two_crossings", "circuit", "horizontal_vertical")

    def test_a_busy_crossing_never_crashes(self):
        for key in self.SCENARIOS:
            for seed in (1, 2, 3, 4):
                with self.subTest(scenario=key, seed=seed):
                    env = build(key, seed=seed)
                    run(env)
                    self.assertEqual(env.total_crashes, 0)

    def test_the_crash_tally_agrees_with_the_wreckage(self):
        for key in self.SCENARIOS:
            with self.subTest(scenario=key):
                env = build(key, seed=2)
                run(env)
                dead = sum(1 for c in env.cars if c.get_death_status())
                self.assertEqual(dead, 2 * env.total_crashes)


class TestPerTickInvariants(unittest.TestCase):
    """Properties checked after every single tick, not just at the end."""

    def setUp(self):
        self.env = build("two_crossings", seed=5)

    def test_nothing_overlaps_at_any_point_in_the_episode(self):
        for tick in range(60):
            self.env.play_step()
            with self.subTest(tick=tick):
                assert_nobody_has_collided(self, self.env)

    def test_the_book_is_consistent_at_every_tick(self):
        for tick in range(40):
            self.env.play_step()
            with self.subTest(tick=tick):
                assert_book_is_consistent(self, self.env)

    def test_no_car_ever_exceeds_its_own_maximum_speed(self):
        for _ in range(60):
            self.env.play_step()
            for car in self.env.cars:
                self.assertLessEqual(car.speed, car.max_speed, car.name)
                self.assertGreaterEqual(car.speed, 0, car.name)

    def test_a_cars_offset_never_runs_off_its_segment(self):
        for _ in range(60):
            self.env.play_step()
            for car in self.env.cars:
                anchor = self.env.reservation_management.get_car_reservation(car.id, 0)
                self.assertLessEqual(abs(car.loc), anchor.segment.length, car.name)

    def test_every_car_holds_at_least_one_reservation(self):
        for _ in range(60):
            self.env.play_step()
            for car in self.env.cars:
                self.assertTrue(
                    self.env.reservation_management.get_car_reservations(car.id),
                    car.name)

    def test_the_clocks_stay_in_step(self):
        for _ in range(30):
            self.env.play_step()
        for car in self.env.cars:
            self.assertEqual(car.time, self.env.time)

    def test_a_reservation_chain_is_always_connected(self):
        for _ in range(60):
            self.env.play_step()
            for car in self.env.cars:
                held = [i.segment for i in
                        self.env.reservation_management.get_car_reservations(car.id)]
                for current, following in zip(held, held[1:]):
                    if isinstance(current, LaneSegment):
                        self.assertIs(current.end_crossing, following, car.name)
                    else:
                        self.assertIn(following, current.connected_segments.values(),
                                      car.name)


class TestIntersectionsClearThemselves(unittest.TestCase):
    """The crossing-claim lease is what keeps a jam from becoming a deadlock."""

    def setUp(self):
        self.env = build("one_crossing", seed=7)

    def test_no_claim_is_held_for_the_whole_episode(self):
        holders = {}
        for _ in range(DEADLOCK_FRAMES * 4):
            self.env.play_step()
            for intersection in self.env.intersections:
                for car_id, _ in intersection.intersection_state.get_priority_items():
                    holders[car_id] = holders.get(car_id, 0) + 1
        for car_id, ticks in holders.items():
            self.assertLess(ticks, DEADLOCK_FRAMES * 4,
                            f"{car_id} held a claim every single tick")

    def test_traffic_keeps_moving_through_the_intersection(self):
        entered = set()
        for _ in range(120):
            self.env.play_step()
            for car in self.env.cars:
                anchor = self.env.reservation_management.get_car_reservation(car.id, 0)
                if isinstance(anchor.segment, CrossingSegment):
                    entered.add(car.id)
        self.assertTrue(entered, "no car ever entered the intersection")

    def test_a_stall_never_lasts_long_enough_to_be_a_deadlock(self):
        worst = 0
        for _ in range(150):
            outcome = self.env.play_step()
            worst = max(worst, self.env.stalled_frames)
            self.assertNotEqual(outcome, "deadlock")
        self.assertLess(worst, DEADLOCK_FRAMES)


class TestEpisodeReset(unittest.TestCase):
    """A reset must leave no trace of the episode before it."""

    def setUp(self):
        self.env = build("one_crossing", seed=9)

    def test_a_second_episode_runs_as_cleanly_as_the_first(self):
        run(self.env, steps=60)
        self.env.reset()
        run(self.env, steps=60)
        self.assertEqual(self.env.total_crashes, 0)
        assert_nobody_has_collided(self, self.env)

    def test_repeated_resets_leave_the_book_consistent(self):
        for _ in range(3):
            run(self.env, steps=30)
            self.env.reset()
            assert_book_is_consistent(self, self.env)

    def test_the_road_network_survives_repeated_resets(self):
        segment_ids = {id(s) for s in self.env.segments}
        for _ in range(3):
            self.env.reset()
        self.assertEqual({id(s) for s in self.env.segments}, segment_ids)

    def test_no_stale_claim_survives_a_reset(self):
        run(self.env, steps=60)
        self.env.reset()
        for intersection in self.env.intersections:
            self.assertEqual(intersection.intersection_state.get_priority_items(), [])

    def test_the_same_seed_reproduces_the_same_episode(self):
        def signature():
            env = build("one_crossing", seed=123)
            run(env, steps=40)
            return [(c.name, c.loc, c.speed, c.score) for c in env.cars]

        self.assertEqual(signature(), signature())


class TestScenarioLoaderIntegration(unittest.TestCase):
    """The parser's output is exactly what the environment takes."""

    def test_every_scenario_key_loads(self):
        for key in available_scenarios():
            with self.subTest(scenario=key):
                scenario = load_scenario(key)
                self.assertIn("roads", scenario)
                self.assertIn("players", scenario)
                self.assertIn("scenario_name", scenario)
                self.assertIn("predefined_cars", scenario)

    def test_a_key_is_case_insensitive(self):
        self.assertEqual(load_scenario("CIRCUIT")["scenario_name"],
                         load_scenario("circuit")["scenario_name"])

    def test_the_loaded_dict_is_the_environments_keyword_set(self):
        random.seed(1)
        Car.reset_id_counter()
        scenario = load_scenario("circuit")
        env = TrafficEnv(roads=scenario["roads"],
                         players=scenario["players"],
                         predefined_cars=scenario["predefined_cars"])
        self.assertEqual(len(env.npc_cars), scenario["players"])

    def test_predefined_cars_are_honoured_end_to_end(self):
        random.seed(1)
        Car.reset_id_counter()
        scenario = load_scenario("two_crossings_predefined")
        env = TrafficEnv(roads=scenario["roads"], players=scenario["players"],
                         predefined_cars=scenario["predefined_cars"])
        specs = scenario["predefined_cars"]
        self.assertTrue(specs, "this scenario is supposed to pin some cars")
        pinned = [c for c in env.npc_cars
                  if any(s.speed == c.speed and s.max_speed == c.max_speed
                         for s in specs)]
        self.assertTrue(pinned)

    def test_an_unknown_scenario_key_is_a_file_error(self):
        with self.assertRaises(FileNotFoundError):
            load_scenario("no_such_scenario")

    def test_the_listing_matches_what_can_be_loaded(self):
        for key in available_scenarios():
            load_scenario(key)


if __name__ == "__main__":
    unittest.main()
