"""Tests for `control.safety.action_shield` -- the SafetyController as a mask.

These cover the shield against a plain `TrafficEnv`, with no RL stack involved;
`manual_tests/test_action_shield.py` covers the same shield inside a Gymnasium
env and a MaskablePPO run, and needs the optional `[rl]` extra.

The shield's soundness argument is that the mask is *conservative*: every joint
action it leaves open is one the SafetyController accepts. That is what the
agreement tests below check, from the shield's side.
"""

import random
import unittest

import numpy as np

from umlsl_sim.config.logic_constants import LANE_MAX_SPEED, MAX_ACC, MAX_DEC
from umlsl_sim.control.safety.action_shield import (
    ACC_ACTIONS,
    FULL_BRAKE_INDEX,
    KEEP_LANE_INDEX,
    LANE_ACTIONS,
    MASK_LENGTH,
    ActionShield,
)
from umlsl_sim.control.safety.safety_controller import SafetyController
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.simulation.traffic_environment import TrafficEnv

from tests.helpers import constant_controller_factory


def _env(players=2, **kwargs):
    random.seed(31337)
    Car.reset_id_counter()
    roads = kwargs.pop("roads", [Road("h1", True, 200, 2, 2),
                                 Road("v1", False, 200, 2, 2)])
    kwargs.setdefault("npc_controller_factory", constant_controller_factory((0, 0)))
    return TrafficEnv(roads=roads, players=players, with_agent=True, **kwargs)


class TestMaskLayout(unittest.TestCase):

    def test_the_blocks_are_sized_from_the_action_space(self):
        self.assertEqual(ACC_ACTIONS, MAX_ACC + MAX_DEC + 1)
        self.assertEqual(LANE_ACTIONS, 3)
        self.assertEqual(MASK_LENGTH, ACC_ACTIONS + LANE_ACTIONS)

    def test_full_braking_is_the_first_acceleration(self):
        self.assertEqual(FULL_BRAKE_INDEX, 0)

    def test_staying_in_lane_is_the_middle_of_the_lane_block(self):
        self.assertEqual(KEEP_LANE_INDEX, ACC_ACTIONS + 1)


class _ShieldFixture(unittest.TestCase):

    def setUp(self):
        self.env = _env()
        self.shield = ActionShield(self.env)


class TestMaskShape(_ShieldFixture):

    def test_a_mask_is_a_boolean_array_of_the_declared_length(self):
        mask = self.shield.action_masks()
        self.assertIsInstance(mask, np.ndarray)
        self.assertEqual(mask.dtype, np.dtype(bool))
        self.assertEqual(mask.shape, (MASK_LENGTH,))

    def test_neither_block_is_ever_empty(self):
        for _ in range(10):
            mask = self.shield.action_masks()
            self.assertTrue(mask[:ACC_ACTIONS].any())
            self.assertTrue(mask[ACC_ACTIONS:].any())
            self.env.play_step(action=(0, 0))

    def test_staying_in_lane_is_always_available(self):
        for _ in range(10):
            self.assertTrue(self.shield.action_masks()[KEEP_LANE_INDEX])
            self.env.play_step(action=(0, 0))

    def test_full_braking_is_always_available(self):
        for _ in range(10):
            self.assertTrue(self.shield.action_masks()[FULL_BRAKE_INDEX])
            self.env.play_step(action=(0, 0))

    def test_the_allowed_accelerations_form_a_prefix(self):
        """Everything at or below the ceiling is safe, so the block is a run of
        trues followed by a run of falses -- never a gap."""
        for _ in range(10):
            block = self.shield.action_masks()[:ACC_ACTIONS]
            allowed = np.flatnonzero(block)
            self.assertEqual(allowed[0], 0)
            self.assertEqual(list(allowed), list(range(len(allowed))))
            self.env.play_step(action=(0, 0))


class TestMaskAgreesWithTheController(_ShieldFixture):

    def test_the_ceiling_is_the_last_allowed_acceleration(self):
        agent = self.env.agent_car
        controller = SafetyController(agent, self.env.cars,
                                      self.env.reservation_management)
        controller.get_max_acceleration()          # burn the warm-up call
        self.shield.action_masks()                 # burn the shield's warm-up too

        for _ in range(15):
            expected = int(np.clip(controller.get_max_acceleration(), -MAX_DEC, MAX_ACC))
            mask = self.shield.action_masks()
            highest = int(np.flatnonzero(mask[:ACC_ACTIONS])[-1]) - MAX_DEC
            self.assertEqual(highest, expected)
            self.env.play_step(action=(0, 0))

    def test_the_lane_block_matches_the_controllers_verdict(self):
        agent = self.env.agent_car
        controller = SafetyController(agent, self.env.cars,
                                      self.env.reservation_management)
        controller.get_max_acceleration()
        self.shield.action_masks()

        for _ in range(15):
            ceiling = int(np.clip(controller.get_max_acceleration(), -MAX_DEC, MAX_ACC))
            reservations = self.env.reservation_management.get_car_reservations(agent.id)
            expected = controller.get_safe_lane_change(reservations, ceiling)
            mask = self.shield.action_masks()
            self.assertEqual(list(mask[ACC_ACTIONS:]), expected)
            self.env.play_step(action=(0, 0))

    def test_the_mask_never_admits_an_acceleration_the_controller_refuses(self):
        agent = self.env.agent_car
        controller = SafetyController(agent, self.env.cars,
                                      self.env.reservation_management)
        controller.get_max_acceleration()
        self.shield.action_masks()

        for _ in range(15):
            ceiling = int(np.clip(controller.get_max_acceleration(), -MAX_DEC, MAX_ACC))
            mask = self.shield.action_masks()
            for index in np.flatnonzero(mask[:ACC_ACTIONS]):
                self.assertLessEqual(int(index) - MAX_DEC, ceiling)
            self.env.play_step(action=(0, 0))


class TestDeadAndMissingAgents(unittest.TestCase):

    def test_a_dead_agent_yields_a_fully_permissive_mask(self):
        env = _env()
        shield = ActionShield(env)
        env.agent_car.handle_car_death(env.reservation_management)
        self.assertTrue(shield.action_masks().all())

    def test_an_env_without_an_agent_yields_a_fully_permissive_mask(self):
        env = _env()
        shield = ActionShield(env)
        env.agent_car = None
        self.assertTrue(shield.action_masks().all())

    def test_a_permissive_mask_still_counts_as_a_step(self):
        env = _env()
        shield = ActionShield(env)
        env.agent_car = None
        shield.action_masks()
        self.assertEqual(shield.stats()["steps"], 1)


class TestControllerCaching(unittest.TestCase):

    def setUp(self):
        self.env = _env()
        self.shield = ActionShield(self.env)

    def test_the_controller_is_built_once_for_a_given_agent(self):
        self.shield.action_masks()
        first = self.shield._controller
        self.shield.action_masks()
        self.assertIs(self.shield._controller, first)

    def test_the_controller_is_rebuilt_when_the_agent_car_is_replaced(self):
        self.shield.action_masks()
        first = self.shield._controller
        self.env.reset()
        self.shield.action_masks()
        self.assertIsNot(self.shield._controller, first)

    def test_the_shield_follows_the_agent_across_a_reset(self):
        self.shield.action_masks()
        self.env.reset()
        self.shield.action_masks()
        self.assertIs(self.shield._controller.car, self.env.agent_car)

    def test_the_rebuilt_controller_sees_the_new_world(self):
        self.shield.action_masks()
        self.env.reset()
        self.shield.action_masks()
        self.assertIs(self.shield._controller.cars, self.env.cars)
        self.assertIs(self.shield._controller.reservation_management,
                      self.env.reservation_management)


class TestStats(unittest.TestCase):

    def setUp(self):
        self.env = _env()
        self.shield = ActionShield(self.env)

    def test_counters_start_at_zero(self):
        stats = self.shield.stats()
        self.assertEqual(stats["steps"], 0)
        self.assertEqual(stats["forced_brake_steps"], 0)
        self.assertEqual(stats["empty_mask_steps"], 0)
        self.assertEqual(stats["mean_allowed_actions"], 0.0)

    def test_steps_counts_the_masks_produced(self):
        for _ in range(5):
            self.shield.action_masks()
        self.assertEqual(self.shield.stats()["steps"], 5)

    def test_the_total_action_count_is_the_size_of_the_joint_space(self):
        self.assertEqual(self.shield.stats()["total_actions"],
                         ACC_ACTIONS * LANE_ACTIONS)

    def test_the_mean_choice_set_is_the_product_of_the_two_blocks(self):
        mask = self.shield.action_masks()
        expected = int(mask[:ACC_ACTIONS].sum()) * int(mask[ACC_ACTIONS:].sum())
        self.assertEqual(self.shield.stats()["mean_allowed_actions"], expected)

    def test_the_mean_never_exceeds_the_joint_space(self):
        for _ in range(10):
            self.shield.action_masks()
            self.env.play_step(action=(0, 0))
        stats = self.shield.stats()
        self.assertLessEqual(stats["mean_allowed_actions"], stats["total_actions"])

    def test_the_empty_mask_counter_stays_at_zero_in_normal_play(self):
        for _ in range(20):
            self.shield.action_masks()
            self.env.play_step(action=(0, 0))
        self.assertEqual(self.shield.stats()["empty_mask_steps"], 0,
                         "a non-zero count means a documented assumption broke")

    def test_a_forced_brake_step_is_counted(self):
        mask = np.zeros(MASK_LENGTH, dtype=bool)
        mask[FULL_BRAKE_INDEX] = True
        mask[KEEP_LANE_INDEX] = True
        self.shield._apply_fallbacks(mask)
        self.assertEqual(self.shield.forced_brake_steps, 1)

    def test_a_wider_choice_set_is_not_a_forced_brake(self):
        mask = np.zeros(MASK_LENGTH, dtype=bool)
        mask[FULL_BRAKE_INDEX] = True
        mask[FULL_BRAKE_INDEX + 1] = True
        mask[KEEP_LANE_INDEX] = True
        self.shield._apply_fallbacks(mask)
        self.assertEqual(self.shield.forced_brake_steps, 0)

    def test_reset_stats_zeroes_the_counters_but_keeps_the_controller(self):
        self.shield.action_masks()
        controller = self.shield._controller
        self.shield.reset_stats()
        self.assertEqual(self.shield.stats()["steps"], 0)
        self.assertIs(self.shield._controller, controller)


class TestFallbacks(unittest.TestCase):
    """The fallbacks are not expected to fire; they exist so a masked policy
    never faces an empty mask, which has no defined behaviour."""

    def setUp(self):
        self.env = _env()
        self.shield = ActionShield(self.env)

    def test_an_empty_acceleration_block_gets_full_braking_back(self):
        mask = np.zeros(MASK_LENGTH, dtype=bool)
        mask[KEEP_LANE_INDEX] = True
        self.shield._apply_fallbacks(mask)
        self.assertTrue(mask[FULL_BRAKE_INDEX])
        self.assertEqual(self.shield.empty_mask_steps, 1)

    def test_an_empty_lane_block_gets_staying_back(self):
        mask = np.zeros(MASK_LENGTH, dtype=bool)
        mask[FULL_BRAKE_INDEX] = True
        self.shield._apply_fallbacks(mask)
        self.assertTrue(mask[KEEP_LANE_INDEX])
        self.assertEqual(self.shield.empty_mask_steps, 1)

    def test_two_empty_blocks_are_counted_twice(self):
        mask = np.zeros(MASK_LENGTH, dtype=bool)
        self.shield._apply_fallbacks(mask)
        self.assertEqual(self.shield.empty_mask_steps, 2)

    def test_a_healthy_mask_is_left_alone(self):
        mask = np.ones(MASK_LENGTH, dtype=bool)
        self.shield._apply_fallbacks(mask)
        self.assertTrue(mask.all())
        self.assertEqual(self.shield.empty_mask_steps, 0)


class TestShieldSideEffects(unittest.TestCase):
    """The one documented side effect: querying the shield may yield the agent's
    intersection claim, exactly as an NPC's own controller does."""

    def setUp(self):
        self.env = _env()
        self.shield = ActionShield(self.env)

    def test_asking_for_a_mask_does_not_move_the_agent(self):
        agent = self.env.agent_car
        before = (agent.loc, agent.speed, agent.time, agent.score)
        for _ in range(5):
            self.shield.action_masks()
        self.assertEqual((agent.loc, agent.speed, agent.time, agent.score), before)

    def test_asking_for_a_mask_does_not_advance_the_environment(self):
        before = self.env.time
        for _ in range(5):
            self.shield.action_masks()
        self.assertEqual(self.env.time, before)

    def test_asking_for_a_mask_does_not_alter_the_reservation_book(self):
        agent = self.env.agent_car
        before = [(str(i.segment), i.begin, i.end)
                  for i in self.env.reservation_management.get_car_reservations(agent.id)]
        for _ in range(5):
            self.shield.action_masks()
        after = [(str(i.segment), i.begin, i.end)
                 for i in self.env.reservation_management.get_car_reservations(agent.id)]
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
