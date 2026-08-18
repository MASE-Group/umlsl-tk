"""Smoke tests: RLMode.TRAIN with MaskablePPO, on both reward profiles.

Choosing MaskablePPO is what turns the safety shield on -- the runner reads
`requires_action_masks` off the algorithm class and attaches an `ActionShield`
to every environment built from its `EnvSpec`, training and evaluation alike.
These tests therefore check the same artefacts as the PPO ones *plus* that the
shield was actually engaged, and they run once per reward profile because the
pairing is a real choice: with the shield masking unsafe actions away,
`INITIAL_REWARD` scores the objective alone, while `SAFETY_AWARE_REWARD`
penalises what the shield already prevents.

Nothing here asserts the mask's contents; that is
`manual_tests/test_action_shield.py`. See `rl_smoke` for the shrunk budgets.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_rl_train_maskable_ppo.py -v
    python manual_tests/test_rl_train_maskable_ppo.py
"""

from rl_smoke import (
    TINY_PPO_PARAMS,
    assert_episode_was_played,
    assert_shield_matches_algorithm,
    assert_trained_model_saved,
    build_runner,
    rl_sandbox,
    run_all_tests,
    run_id,
    save_hyperparameters,
    train_runner,
)

from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.modes import RLMode
from umlsl_sim.rl.rewards.reward_types import RewardType

ALGORITHM = RLAlgorithmType.MASKABLE_PPO


class TestMaskablePPOTraining:
    """A whole TRAIN run under the shield, once per reward profile."""

    def test_trains_with_the_initial_reward(self):
        """The intended pairing: the shield handles safety, so the reward is
        free to speak only about the objective."""
        with rl_sandbox():
            runner = train_runner(ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)
            assert_shield_matches_algorithm(runner, ALGORITHM)

    def test_trains_with_the_safety_aware_reward(self):
        """Belt and braces: masked *and* penalised. Redundant by design, but a
        configuration the runner has to keep accepting."""
        with rl_sandbox():
            runner = train_runner(ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            runner.run()

            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)
            assert_shield_matches_algorithm(runner, ALGORITHM)

    def test_evaluation_environment_is_shielded_too(self):
        """A policy evaluated without its shield is not the policy that
        trained, so the spec the evaluation environment is built from must
        carry the masking flag."""
        with rl_sandbox():
            runner = train_runner(ALGORITHM, RewardType.INITIAL_REWARD)

            assert runner.env_spec.uses_action_masks
            assert runner.env_spec.headless().uses_action_masks

            evaluation_env, evaluation_shield = runner.env_spec.headless().build()
            try:
                assert evaluation_shield is not None
                assert evaluation_env.unwrapped.action_shield is evaluation_shield
            finally:
                evaluation_env.close()

            runner.env.close()

    def test_trained_model_can_be_loaded_and_watched(self):
        """The round trip through `rl_io`, on the maskable side: loading picks
        the sb3-contrib evaluation helpers, which pass the mask into every
        prediction."""
        with rl_sandbox():
            trained = train_runner(ALGORITHM, RewardType.INITIAL_REWARD)
            trained.run()

            watched = build_runner(
                RLMode.LOAD_TRAINED_MODEL,
                ALGORITHM,
                RewardType.INITIAL_REWARD,
                id_model=run_id(trained.model_path),
            )
            watched.run()

            assert_episode_was_played(watched)
            assert_shield_matches_algorithm(watched, ALGORITHM)

    def test_trains_from_saved_hyperparameters(self):
        """MaskablePPO shares PPO's parameter space, so a parquet written by a
        search is loadable here in exactly the same way."""
        with rl_sandbox():
            params_id = save_hyperparameters(ALGORITHM, RewardType.SAFETY_AWARE_REWARD)

            runner = build_runner(
                RLMode.TRAIN,
                ALGORITHM,
                RewardType.SAFETY_AWARE_REWARD,
                id_hyperparams=params_id,
            )
            runner.run()

            assert runner.rl_algorithm.algorithm.n_steps == TINY_PPO_PARAMS["n_steps"]
            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)


if __name__ == "__main__":
    run_all_tests(TestMaskablePPOTraining)
    print("\nAll MaskablePPO training smoke tests passed.")
