"""Tests for the safety-shield training mechanism (masked actions).

Covers three things:

* the mask agrees with the SafetyController it is derived from, and is
  conservative rather than permissive;
* the shield is opt-in -- an env without one allows every action, so the
  reward-based profiles are unaffected;
* MaskablePPO trains and predicts through the shield, and never returns a
  masked-out action.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_action_shield.py -v
    python manual_tests/test_action_shield.py
"""
import numpy as np

from umlsl_sim.car_control.action_shield import (
    ACC_ACTIONS,
    LANE_ACTIONS,
    MASK_LENGTH,
    ActionShield,
)
from umlsl_sim.car_control.safety_controller import SafetyController
from umlsl_sim.constants import MAX_ACC, MAX_DEC
from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_registry import get_rl_algo
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import (
    ObservationModelType,
)
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_registry import (
    get_observation_model,
)
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_registry import get_reward_model


def _build_env(scenario_key: str = "CIRCUIT", reward: RewardType = RewardType.INITIAL_REWARD):
    """A small UMLSL gymnasium env, shield not yet attached."""
    scenario = load_scenario(scenario_key)

    game_model = TrafficEnv(
        roads=scenario["roads"],
        players=scenario["players"],
        predefined_cars=scenario["predefined_cars"],
        rl_mode=RLMode.TRAIN,
    )

    obs_model = get_observation_model(ObservationModelType.NUMERIC_OBSERVATION)(game_model)
    return get_reward_model(reward)(
        game_model=game_model,
        observation_model=obs_model,
        render_mode=None,
        show_reservation=False,
    )


def _decode(index: int) -> int:
    """Acceleration encoded by an index of the first action dimension."""
    return index - MAX_DEC


class TestMaskShape:
    """The mask must match what MultiDiscrete masking expects."""

    def test_length_matches_action_space(self):
        env = _build_env()
        assert MASK_LENGTH == int(env.action_space.nvec.sum())
        assert (ACC_ACTIONS, LANE_ACTIONS) == tuple(int(n) for n in env.action_space.nvec)
        env.close()

    def test_unshielded_env_allows_everything(self):
        """Reward-based safety must be untouched: no shield, no restrictions."""
        env = _build_env()
        env.reset(seed=7)

        assert env.action_shield is None
        assert env.action_masks().all()
        env.close()

    def test_enable_is_idempotent(self):
        env = _build_env()
        first = env.enable_action_shield()
        assert env.enable_action_shield() is first
        env.close()


class TestMaskAgreesWithController:
    """The mask is a re-encoding of the SafetyController's verdict."""

    def test_allowed_accelerations_are_at_most_the_controller_maximum(self):
        env = _build_env()
        shield = env.enable_action_shield()
        env.reset(seed=11)

        for _ in range(25):
            mask = env.action_masks()
            agent = env.game_model.agent_car
            if agent is None or agent.get_death_status():
                break

            # Same query the shield made, on the same pre-step state. The
            # controller is stateful across calls (first_go, priority drops),
            # so read the shield's own controller rather than a fresh one.
            controller = shield._controller_for(agent)
            allowed = [_decode(i) for i in range(ACC_ACTIONS) if mask[i]]

            assert allowed, "acceleration mask must never be empty"
            # Contiguous from full braking up to the safe maximum.
            assert allowed == list(range(-MAX_DEC, max(allowed) + 1))
            assert max(allowed) <= controller.get_max_acceleration()

            obs, _r, done, truncated, _i = env.step(env.action_space.sample())
            if done or truncated:
                break
        env.close()

    def test_lane_mask_holds_for_every_allowed_acceleration(self):
        """Per-dimension masks are only sound if the lane verdict survives any
        acceleration the mask permits -- the conservativeness claim."""
        env = _build_env()
        shield = env.enable_action_shield()
        env.reset(seed=3)

        checked = 0
        for _ in range(25):
            mask = env.action_masks()
            agent = env.game_model.agent_car
            if agent is None or agent.get_death_status():
                break

            controller = shield._controller_for(agent)
            reservations = env.game_model.reservation_management.get_car_reservations(agent.id)
            allowed_acc = [_decode(i) for i in range(ACC_ACTIONS) if mask[i]]

            for acc in allowed_acc:
                verdict = controller.get_safe_lane_change(reservations, acc)
                for lane_index in range(LANE_ACTIONS):
                    if mask[ACC_ACTIONS + lane_index]:
                        assert verdict[lane_index], (
                            f"mask allows lane action {lane_index - 1} which the "
                            f"controller rejects at acceleration {acc}"
                        )
                checked += 1

            obs, _r, done, truncated, _i = env.step(env.action_space.sample())
            if done or truncated:
                break

        assert checked > 0, "test exercised no states"
        env.close()

    def test_staying_in_lane_is_always_available(self):
        env = _build_env()
        env.enable_action_shield()
        env.reset(seed=5)

        for _ in range(30):
            mask = env.action_masks()
            assert mask[ACC_ACTIONS:].any(), "lane mask must never be empty"
            obs, _r, done, truncated, _i = env.step(env.action_space.sample())
            if done or truncated:
                break
        env.close()

    def test_mask_never_empty_and_dtype_is_bool(self):
        env = _build_env()
        env.enable_action_shield()
        env.reset(seed=13)

        for _ in range(30):
            mask = env.action_masks()
            assert mask.dtype == np.bool_
            assert mask.shape == (MASK_LENGTH,)
            assert mask[:ACC_ACTIONS].any() and mask[ACC_ACTIONS:].any()
            obs, _r, done, truncated, _i = env.step(env.action_space.sample())
            if done or truncated:
                break

        assert env.action_shield.stats()["empty_mask_steps"] == 0
        env.close()

    def test_dead_agent_yields_permissive_mask(self):
        """The env terminates on the death step, but the policy still has to
        pick an action for it -- an all-masked state would be undefined."""
        env = _build_env()
        env.enable_action_shield()
        env.reset(seed=17)

        env.game_model.agent_car.handle_car_death(env.game_model.reservation_management)
        assert env.action_masks().all()
        env.close()

    def test_shield_follows_the_agent_across_reset(self):
        """TrafficEnv.reset() builds a new agent car; the cached controller must
        not keep pointing at the old one."""
        env = _build_env()
        shield = env.enable_action_shield()
        env.reset(seed=19)
        env.action_masks()
        first_car = shield._car

        env.reset(seed=23)
        env.action_masks()

        assert shield._car is env.game_model.agent_car
        assert shield._car is not first_car
        env.close()


class TestShieldStats:
    def test_counters_track_steps_and_choice_set(self):
        env = _build_env()
        shield = env.enable_action_shield()
        env.reset(seed=29)

        for _ in range(10):
            env.action_masks()
            obs, _r, done, truncated, _i = env.step(env.action_space.sample())
            if done or truncated:
                break

        stats = shield.stats()
        assert stats["steps"] > 0
        assert 0 < stats["mean_allowed_actions"] <= ACC_ACTIONS * LANE_ACTIONS
        assert stats["empty_mask_steps"] == 0

        shield.reset_stats()
        assert shield.stats()["steps"] == 0
        env.close()


class TestMaskablePPOIntegration:
    """The shield must survive the trip through sb3-contrib."""

    def test_algorithm_is_registered_and_flagged(self):
        algo_class = get_rl_algo(RLAlgorithmType.MASKABLE_PPO)
        assert algo_class is not None
        assert algo_class.requires_action_masks is True
        assert get_rl_algo(RLAlgorithmType.PPO).requires_action_masks is False

    def test_trains_and_respects_the_mask(self):
        from sb3_contrib import MaskablePPO

        env = _build_env()
        shield = env.enable_action_shield()

        model = MaskablePPO("MlpPolicy", env, n_steps=16, batch_size=8, n_epochs=1, verbose=0)
        model.learn(total_timesteps=32)

        obs, _info = env.reset(seed=31)
        for _ in range(20):
            mask = env.action_masks()
            action, _states = model.predict(obs, deterministic=True, action_masks=mask)

            assert env.action_space.contains(action)
            assert mask[int(action[0])], "policy chose a masked-out acceleration"
            assert mask[ACC_ACTIONS + int(action[1])], "policy chose a masked-out lane change"

            obs, _reward, done, truncated, _info = env.step(action)
            if done or truncated:
                break

        assert shield.stats()["steps"] > 0
        env.close()

    def test_mask_reaches_the_algorithm_through_monitor(self):
        """Training wraps the env in Monitor; sb3-contrib finds action_masks()
        through get_wrapper_attr, and this is the regression guard for it."""
        from stable_baselines3.common.monitor import Monitor
        from sb3_contrib.common.maskable.utils import get_action_masks

        env = _build_env()
        env.enable_action_shield()
        monitored = Monitor(env)
        monitored.reset(seed=37)

        mask = get_action_masks(monitored)
        assert mask.shape == (MASK_LENGTH,)
        assert mask.any()
        monitored.close()


if __name__ == "__main__":
    for cls in (TestMaskShape, TestMaskAgreesWithController, TestShieldStats,
                TestMaskablePPOIntegration):
        instance = cls()
        for name in sorted(n for n in dir(instance) if n.startswith("test_")):
            getattr(instance, name)()
            print(f"{cls.__name__}.{name} passed")

    print("\nAll safety-shield tests passed.")
