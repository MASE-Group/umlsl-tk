"""
Very simple integration test that creates a Stable Baselines3 PPO agent
and trains it for a few timesteps on the UMLSL gymnasium environment.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_train.py -v   # via pytest
    python manual_tests/test_train.py      # directly, as a script
"""
import numpy as np

from stable_baselines3 import PPO

from umlsl_sim.scenario.loader import load_scenario
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.rl.modes import RLMode
from umlsl_sim.rl.observations.observation_model_types import ObservationModelType
from umlsl_sim.rl.observations.observation_registry import get_observation_model
from umlsl_sim.rl.rewards.reward_types import RewardType
from umlsl_sim.rl.rewards.reward_registry import get_reward_model


def _build_env(scenario_key: str = "CIRCUIT"):
    """Construct a small UMLSL gymnasium env ready for RL."""
    scenario = load_scenario(scenario_key)

    # The underlying traffic simulation
    game_model = TrafficEnv(
        roads=scenario["roads"],
        players=scenario["players"],
        predefined_cars=scenario["predefined_cars"],
        with_agent=True,
    )

    # The registries are populated by decorators that run on module import;
    # importing the enum module pulls in its package __init__, which imports
    # every sibling model module for exactly that side effect.
    obs_model_cls = get_observation_model(ObservationModelType.NUMERIC_OBSERVATION)
    obs_model = obs_model_cls(game_model)

    env_cls = get_reward_model(RewardType.INITIAL_REWARD)
    env = env_cls(
        game_model=game_model,
        observation_model=obs_model,
        render_mode=None,
        show_reservation=False,
    )
    return env


class TestSimplePPOTraining:
    """Sanity-check that the MLSL env is compatible with Stable Baselines3 PPO."""

    def test_env_compatibility(self):
        """Reset + random steps must return correct Gymnasium tuples."""
        env = _build_env("CIRCUIT")
        obs, info = env.reset(seed=42)

        assert isinstance(obs, np.ndarray)
        assert obs.dtype == np.float32
        assert env.observation_space.contains(obs)

        for _ in range(5):
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)

            assert isinstance(obs, np.ndarray)
            assert env.observation_space.contains(obs)
            assert isinstance(reward, (int, float))
            assert isinstance(terminated, bool)
            assert isinstance(truncated, bool)
            assert isinstance(info, dict)

            if terminated or truncated:
                obs, info = env.reset()

        env.close()

    def test_ppo_runs(self):
        """Instantiate PPO and train for a handful of timesteps."""
        env = _build_env("CIRCUIT")
        model = PPO(
            "MlpPolicy",
            env,
            n_steps=8,
            batch_size=8,
            n_epochs=1,
            verbose=0,
        )
        model.learn(total_timesteps=20)
        env.close()

        # Basic sanity: model exists and has policy weights
        assert model.policy is not None

    def test_ppo_predict(self):
        """Train a tiny bit, then predict deterministic + stochastic actions."""
        env = _build_env("CIRCUIT")
        model = PPO(
            "MlpPolicy",
            env,
            n_steps=8,
            batch_size=8,
            n_epochs=1,
            verbose=0,
        )
        model.learn(total_timesteps=16)

        obs, _ = env.reset()
        action, _states = model.predict(obs, deterministic=True)
        assert env.action_space.contains(action)

        action, _states = model.predict(obs, deterministic=False)
        assert env.action_space.contains(action)

        env.close()


if __name__ == "__main__":
    # Quick self-test when executed directly
    t = TestSimplePPOTraining()
    t.test_env_compatibility()
    print("test_env_compatibility passed")

    t.test_ppo_runs()
    print("test_ppo_runs passed")

    t.test_ppo_predict()
    print("test_ppo_predict passed")

    print("\nAll basic Stable Baselines3 integration tests passed.")