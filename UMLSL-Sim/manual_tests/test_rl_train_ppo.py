"""Smoke tests: RLMode.TRAIN with plain PPO, on both reward profiles.

PPO sees every action, so safety is whatever its reward makes of it -- these
tests therefore run the same training path twice, once per profile, because the
reward profile is the environment class here and not a parameter of it.

What is asserted is that a training run *completes and produces its artefacts*:
an episode was played and reported, EvalCallback checkpointed a model where
`rl_io` will look for it, and no shield was attached behind PPO's back. Nothing
asserts that the agent improved; on 64 timesteps it cannot, and a test that
demanded it would be a test of luck. See `rl_smoke` for the shrunk budgets.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_rl_train_ppo.py -v
    python manual_tests/test_rl_train_ppo.py
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

ALGORITHM = RLAlgorithmType.PPO


class TestPPOTraining:
    """A whole TRAIN run, once per reward profile."""

    def test_trains_with_the_initial_reward(self):
        """The objective-only profile: goals, crashes and deadlock, no shield.

        Pairing it with plain PPO leaves nothing telling the agent about
        safety, which is a legitimate configuration and has to keep running.
        """
        with rl_sandbox():
            runner = train_runner(ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)
            assert_shield_matches_algorithm(runner, ALGORITHM)

    def test_trains_with_the_safety_aware_reward(self):
        """The profile PPO is meant to be paired with: unsafe accelerations and
        lane changes are penalised, so the SafetyController is consulted on
        every step of the run."""
        with rl_sandbox():
            runner = train_runner(ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            runner.run()

            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)
            assert_shield_matches_algorithm(runner, ALGORITHM)

    def test_trained_model_can_be_loaded_and_watched(self):
        """Train, then load the checkpoint back through LOAD_TRAINED_MODEL.

        The round trip is the part of `rl_io` a training run cannot check on
        its own: the model is saved by EvalCallback under a path the *reader*
        composes, so the two agreeing is worth a test.
        """
        with rl_sandbox():
            trained = train_runner(ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            trained.run()

            watched = build_runner(
                RLMode.LOAD_TRAINED_MODEL,
                ALGORITHM,
                RewardType.SAFETY_AWARE_REWARD,
                id_model=run_id(trained.model_path),
            )
            watched.run()

            assert_episode_was_played(watched)

    def test_trains_from_saved_hyperparameters(self):
        """TRAIN with an `id_hyperparams` reads a search's parquet back and
        builds the agent from it, rather than from the library defaults."""
        with rl_sandbox():
            params_id = save_hyperparameters(ALGORITHM, RewardType.INITIAL_REWARD)

            runner = build_runner(
                RLMode.TRAIN,
                ALGORITHM,
                RewardType.INITIAL_REWARD,
                id_hyperparams=params_id,
            )
            runner.run()

            assert runner.rl_algorithm.algorithm.n_steps == TINY_PPO_PARAMS["n_steps"]
            assert_episode_was_played(runner)
            assert_trained_model_saved(runner)


if __name__ == "__main__":
    run_all_tests(TestPPOTraining)
    print("\nAll PPO training smoke tests passed.")
