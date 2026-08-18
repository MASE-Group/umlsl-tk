"""Integration: the control layer against a live simulation.

The unit tests ask each controller what it would decide from a state built by
hand. These run the decisions back into the environment, which is where the
interesting failures live: a controller that is individually correct can still
be collectively wrong, because every car decides against pre-tick state and the
actions are then applied one after another.

Also covered here: the agent-driven path (`with_agent=True`), the shield in
front of it, and a record/replay round trip through `GameHistory`.
"""

import random
import unittest

import numpy as np

from umlsl_sim.config.logic_constants import (
    CLAIM_TIME,
    LANECHANGE_TIME_STEPS,
    LEFT_LANE_CHANGE,
    MAX_ACC,
    MAX_DEC,
    NO_LANE_CHANGE,
    RIGHT_LANE_CHANGE,
    WITHDRAW_CLAIM,
)
from umlsl_sim.control.astar.astar_car_controller import AstarCarController
from umlsl_sim.control.safety.action_shield import ACC_ACTIONS, ActionShield
from umlsl_sim.control.safety.safety_controller import SafetyController
from umlsl_sim.scenario.loader import load_scenario
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.event_checks import collision_check
from umlsl_sim.simulation.ports import NullRenderer
from umlsl_sim.simulation.traffic_environment import TrafficEnv


def build(scenario_key="one_crossing", seed=1, players=6, with_agent=False,
          npc_controller_factory=None):
    random.seed(seed)
    Car.reset_id_counter()
    scenario = load_scenario(scenario_key)
    return TrafficEnv(
        roads=scenario["roads"],
        players=players,
        predefined_cars=scenario["predefined_cars"],
        with_agent=with_agent,
        npc_controller_factory=npc_controller_factory,
    )


class TestAstarControllerDrivesTheEnvironment(unittest.TestCase):

    def setUp(self):
        self.env = build(players=6, seed=21)

    def test_the_default_controller_is_wired_to_each_npc(self):
        for controller in self.env.controllers:
            self.assertIsInstance(controller, AstarCarController)
            self.assertIn(controller.car, self.env.npc_cars)
            self.assertIs(controller.cars, self.env.cars)
            self.assertIs(controller.reservation_management,
                          self.env.reservation_management)

    def test_simultaneous_decisions_never_produce_a_collision(self):
        """Every controller decides against the same pre-tick state, so two
        cars can pick the same gap. Neither is stopped from claiming it; what
        keeps them apart is that each sees the other's claim on the ticks
        that follow, and the first one asked gives its claim back."""
        for _ in range(150):
            self.env.play_step()
            for i, first in enumerate(self.env.cars):
                for second in self.env.cars[i + 1:]:
                    self.assertFalse(
                        collision_check(first, second, self.env.reservation_management))

    def test_every_action_stays_inside_the_declared_range(self):
        for _ in range(80):
            for controller in self.env.controllers:
                acceleration, lane_change = controller.get_action()
                self.assertGreaterEqual(acceleration, -MAX_DEC)
                self.assertLessEqual(acceleration, MAX_ACC)
                self.assertIn(lane_change, (RIGHT_LANE_CHANGE, NO_LANE_CHANGE,
                                            LEFT_LANE_CHANGE, WITHDRAW_CLAIM))
            self.env.play_step()

    def test_a_replacement_controller_is_used_instead(self):
        class AlwaysBrake:
            def __init__(self, car, cars, reservation_management):
                self.car = car

            def get_action(self):
                return (-MAX_DEC, 0)

        env = build(players=4, seed=3, npc_controller_factory=AlwaysBrake)
        for _ in range(6):
            env.play_step()
        for car in env.cars:
            self.assertEqual(car.speed, 0, "every car was told to brake flat out")

    def test_the_simulation_layer_imports_without_the_control_layer(self):
        """`_default_npc_controller_factory` imports A* inside the function, so
        a caller that supplies its own factory never pulls the control layer in."""
        import umlsl_sim.simulation.traffic_environment as module
        source = open(module.__file__).read()
        self.assertNotIn("\nfrom umlsl_sim.control", source,
                         "the control layer must not be a module-level import")


class TestAgentDrivenEpisode(unittest.TestCase):

    def setUp(self):
        self.env = build(players=5, seed=17, with_agent=True)

    def test_the_agent_is_driven_by_the_action_it_is_handed(self):
        agent = self.env.agent_car
        before = agent.speed
        self.env.play_step(action=(MAX_ACC, 0))
        self.assertEqual(agent.speed, min(before + MAX_ACC, agent.max_speed))

    def test_an_unshielded_agent_that_ignores_safety_does_crash(self):
        """The environment does not protect the agent -- that is the shield's
        job, and its absence is what makes the shield worth having.

        Seeded deliberately: an agent flooring it does not crash in *every*
        layout, because the NPCs around it give way. This one it does, which is
        the point -- compare `TestShieldedAgentEpisode`, where the same
        greedy policy through the mask never dies.
        """
        env = build(players=5, seed=17, with_agent=True)
        for _ in range(120):
            env.play_step(action=(MAX_ACC, 0))
            if env.agent_car.get_death_status():
                break
        self.assertTrue(env.agent_car.get_death_status())
        self.assertEqual(env.total_crashes, 1)

    def test_the_npcs_carry_on_around_a_crashed_agent(self):
        self.env.agent_car.handle_car_death(self.env.reservation_management)
        for _ in range(60):
            outcome = self.env.play_step(action=(0, 0))
            if outcome is not None:
                break
        living = [c for c in self.env.npc_cars if not c.get_death_status()]
        self.assertTrue(living, "a dead agent must not take the NPCs with it")

    def test_a_reset_gives_the_agent_a_fresh_car(self):
        first = self.env.agent_car
        self.env.reset()
        self.assertIsNot(self.env.agent_car, first)
        self.assertFalse(self.env.agent_car.get_death_status())


class TestShieldedAgentEpisode(unittest.TestCase):
    """A shielded agent choosing the most aggressive action the mask allows."""

    def setUp(self):
        self.env = build(players=5, seed=23, with_agent=True)
        self.shield = ActionShield(self.env)

    def _greedy_action(self):
        """Fastest acceleration, and the boldest lane command on offer:
        change if a change is allowed, otherwise hold, and withdraw a claim
        only when the mask leaves nothing else -- which is exactly when the
        claimed space has turned out to belong to somebody else."""
        mask = self.shield.action_masks()
        acceleration = int(np.flatnonzero(mask[:ACC_ACTIONS])[-1]) - MAX_DEC
        lane_choices = np.flatnonzero(mask[ACC_ACTIONS:])
        without_withdraw = [c for c in lane_choices if int(c) - 1 != WITHDRAW_CLAIM]
        lane_change = int((without_withdraw or lane_choices)[-1]) - 1
        return acceleration, lane_change

    def test_a_shielded_agent_never_crashes(self):
        for _ in range(150):
            outcome = self.env.play_step(action=self._greedy_action())
            self.assertFalse(self.env.agent_car.get_death_status(),
                             "the shield admitted an action that killed the agent")
            if outcome is not None:
                break

    def test_a_shielded_agent_still_gets_somewhere(self):
        for _ in range(150):
            self.env.play_step(action=self._greedy_action())
        self.assertGreater(self.shield.stats()["mean_allowed_actions"], 1,
                           "a shield that only ever allows one action is useless")

    def test_the_shield_never_had_to_use_a_fallback(self):
        for _ in range(150):
            self.env.play_step(action=self._greedy_action())
        self.assertEqual(self.shield.stats()["empty_mask_steps"], 0)

    def test_the_shield_keeps_following_the_agent_across_resets(self):
        for _ in range(20):
            self.env.play_step(action=self._greedy_action())
        self.env.reset()
        for _ in range(20):
            self.env.play_step(action=self._greedy_action())
        self.assertIs(self.shield._controller.car, self.env.agent_car)

    def test_the_stats_add_up_over_a_run(self):
        steps = 40
        for _ in range(steps):
            self.env.play_step(action=self._greedy_action())
        stats = self.shield.stats()
        self.assertEqual(stats["steps"], steps)
        self.assertLessEqual(stats["forced_brake_steps"], stats["steps"])


class TestLaneChangeLifecycle(unittest.TestCase):
    """The claim -> reservation -> landing sequence, driven through the env."""

    def setUp(self):
        # A multi-lane scenario, so the agent has somewhere to move to.
        self.env = build("two_crossings", players=5, seed=17, with_agent=True)
        self.rm = self.env.reservation_management
        self.agent = self.env.agent_car

    def _adjacent(self):
        """A lane command the agent can actually claim from where it stands."""
        for command in (LEFT_LANE_CHANGE, RIGHT_LANE_CHANGE):
            if self.agent.get_adjacent_lane_segment(self.rm, command) is not None:
                return command
        self.skipTest("the agent has no neighbouring lane to move into")

    def test_a_claim_becomes_a_reservation_and_then_a_lane(self):
        command = self._adjacent()
        target = self.agent.get_adjacent_lane_segment(self.rm, command)
        self.env.play_step(action=(0, command))
        self.assertFalse(self.rm.get_lane_change_claim(self.agent.id).committed)

        for _ in range(CLAIM_TIME):
            self.env.play_step(action=(0, NO_LANE_CHANGE))
        claim = self.rm.get_lane_change_claim(self.agent.id)
        if claim is None:
            self.skipTest("the agent left the segment before the claim committed")
        self.assertTrue(claim.committed)

        for _ in range(LANECHANGE_TIME_STEPS):
            self.env.play_step(action=(0, NO_LANE_CHANGE))
        self.assertIsNone(self.rm.get_lane_change_claim(self.agent.id))
        self.assertIs(self.rm.get_car_reservation(self.agent.id, 0).segment, target)

    def test_a_withdrawn_claim_leaves_the_agent_where_it_was(self):
        command = self._adjacent()
        source = self.rm.get_car_reservation(self.agent.id, 0).segment
        target = self.agent.get_adjacent_lane_segment(self.rm, command)
        self.env.play_step(action=(0, command))
        self.env.play_step(action=(0, WITHDRAW_CLAIM))

        self.assertIsNone(self.rm.get_lane_change_claim(self.agent.id))
        self.assertEqual(self.rm.get_cars_changing_into_segment(target), [])
        for _ in range(CLAIM_TIME + LANECHANGE_TIME_STEPS):
            self.env.play_step(action=(0, NO_LANE_CHANGE))
        self.assertIs(self.rm.get_car_reservation(self.agent.id, 0).segment, source)

    def test_a_committed_change_ignores_a_withdrawal(self):
        command = self._adjacent()
        self.env.play_step(action=(0, command))
        for _ in range(CLAIM_TIME):
            self.env.play_step(action=(0, NO_LANE_CHANGE))
        if self.rm.get_lane_change_claim(self.agent.id) is None:
            self.skipTest("the agent left the segment before the claim committed")

        self.env.play_step(action=(0, WITHDRAW_CLAIM))
        claim = self.rm.get_lane_change_claim(self.agent.id)
        self.assertIsNotNone(claim, "a committed change cannot be given back")
        self.assertTrue(claim.committed)


class TestSafetyControllerAgainstLiveTraffic(unittest.TestCase):
    """The safety oracle, checked against what actually happens next."""

    def setUp(self):
        self.env = build(players=6, seed=29, with_agent=True)
        self.controller = SafetyController(
            self.env.agent_car, self.env.cars, self.env.reservation_management)
        self.controller.get_max_acceleration()

    def test_following_the_ceiling_keeps_the_agent_alive(self):
        for _ in range(150):
            ceiling = self.controller.get_max_acceleration()
            outcome = self.env.play_step(action=(ceiling, 0))
            self.assertFalse(self.env.agent_car.get_death_status())
            if outcome is not None:
                break

    def test_the_ceiling_is_a_legal_acceleration(self):
        for _ in range(60):
            ceiling = self.controller.get_max_acceleration()
            self.assertGreaterEqual(ceiling, -MAX_DEC)
            self.assertLessEqual(ceiling, MAX_ACC)
            self.assertGreaterEqual(self.env.agent_car.speed + ceiling, 0)
            self.env.play_step(action=(ceiling, 0))

    def test_the_ceiling_never_pushes_past_the_cars_maximum(self):
        for _ in range(60):
            agent = self.env.agent_car
            ceiling = self.controller.get_max_acceleration()
            self.assertLessEqual(agent.speed + ceiling, agent.max_speed)
            self.env.play_step(action=(ceiling, 0))


class TestRecordAndReplay(unittest.TestCase):
    """A whole episode recorded through `TrafficEnv` and replayed back."""

    def setUp(self):
        self.env = build(players=4, seed=41)

    def test_an_episode_is_recorded_as_it_runs(self):
        for _ in range(20):
            self.env.play_step()
        self.assertEqual(self.env.game_history.action_length, 20 * len(self.env.cars))

    def test_the_recording_carries_the_state_it_started_from(self):
        for _ in range(10):
            self.env.play_step()
        self.assertEqual(len(self.env.game_history.car_snapshots), len(self.env.cars))

    def test_a_recorded_episode_replays(self):
        for _ in range(20):
            self.env.play_step()
        renderer = NullRenderer()
        self.env.game_history.replay(renderer)

    def test_a_replay_leaves_the_live_simulation_untouched(self):
        for _ in range(20):
            self.env.play_step()
        before = [(c.loc, c.speed, c.time, c.score) for c in self.env.cars]
        self.env.game_history.replay()
        self.assertEqual([(c.loc, c.speed, c.time, c.score) for c in self.env.cars],
                         before)

    def test_a_replay_reproduces_the_recorded_run(self):
        """Same start, same actions, same machinery -- so the same positions."""
        ticks = 20
        for _ in range(ticks):
            self.env.play_step()
        expected = [(c.loc, c.speed) for c in self.env.cars]

        class Capture(NullRenderer):
            def __init__(self):
                super().__init__()
                self.cars = None

            def bind(self, cars, roads, reservation_management=None):
                self.cars = list(cars)

        renderer = Capture()
        self.env.game_history.replay(renderer)
        replayed = [(c.loc, c.speed) for c in renderer.cars]
        self.assertEqual(replayed, expected)

    def test_a_reset_starts_a_fresh_recording(self):
        for _ in range(10):
            self.env.play_step()
        self.env.reset()
        self.assertEqual(self.env.game_history.action_length, 0)
        for _ in range(5):
            self.env.play_step()
        self.assertEqual(self.env.game_history.action_length, 5 * len(self.env.cars))


if __name__ == "__main__":
    unittest.main()
