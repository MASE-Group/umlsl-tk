"""Smoke tests: Optuna hyperparameter search for MaskablePPO, both profiles.

Searching for a masking algorithm differs from searching for PPO in one way
that matters and is easy to lose: every environment a trial builds -- the one
it trains on and the one it is evaluated on -- must carry the safety shield,
and the evaluation callback must be the sb3-contrib one that passes the mask
into each prediction. A search that scored masked policies without their masks
would tune for an agent nobody runs.

Otherwise the shape is the PPO file's: two trials of 64 timesteps, run once per
reward profile, asserting that the search completes and files its results.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_rl_optimize_maskable_ppo.py -v
    python manual_tests/test_rl_optimize_maskable_ppo.py
"""

from rl_smoke import (
    assert_episode_was_played,
    assert_search_results_saved,
    assert_shield_matches_algorithm,
    assert_trained_model_saved,
    best_params_of,
    build_runner,
    rl_sandbox,
    run_all_tests,
    run_id,
)

from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.modes import RLMode
from umlsl_sim.rl.rewards.reward_types import RewardType

ALGORITHM = RLAlgorithmType.MASKABLE_PPO


class TestMaskablePPOHyperparameterSearch:
    """RLMode.OPTIMIZE under the shield, once per reward profile."""

    def test_searches_with_the_initial_reward(self):
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            assert_search_results_saved(runner)
            assert ALGORITHM.name in runner.hyperparams_path

    def test_searches_with_the_safety_aware_reward(self):
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            runner.run()

            assert_search_results_saved(runner)

    def test_trials_are_built_with_the_shield(self):
        """The spec handed to the search carries the masking flag, so each
        trial's environments get a shield of their own -- headless, because a
        trial is never watched."""
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)

            trial_spec = runner.env_spec.headless()
            assert trial_spec.uses_action_masks

            trial_env, trial_shield = trial_spec.build()
            try:
                assert trial_shield is not None
                assert trial_env.unwrapped.action_shield is trial_shield
            finally:
                trial_env.close()

            runner.env.close()

    def test_trial_evaluation_uses_the_maskable_callback(self):
        """Pruning decisions come from the trial's evaluations, so those have
        to be masked evaluations; the callback's base class is where that is
        decided."""
        from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
        from stable_baselines3.common.callbacks import EvalCallback

        from umlsl_sim.rl.hyperparameters.optuna_search import _trial_eval_callback

        masked_callback = _trial_eval_callback(requires_action_masks=True)
        plain_callback = _trial_eval_callback(requires_action_masks=False)

        assert issubclass(masked_callback, MaskableEvalCallback)
        assert issubclass(plain_callback, EvalCallback)
        assert not issubclass(plain_callback, MaskableEvalCallback)

    def test_search_output_is_loadable_by_training(self):
        """Search, then train the masked agent from what the search wrote."""
        with rl_sandbox():
            search = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)
            search.run()

            training = build_runner(
                RLMode.TRAIN,
                ALGORITHM,
                RewardType.INITIAL_REWARD,
                id_hyperparams=run_id(search.hyperparams_path),
            )
            training.run()

            assert training.rl_algorithm.algorithm.n_steps == best_params_of(search)["n_steps"]
            assert_episode_was_played(training)
            assert_trained_model_saved(training)
            assert_shield_matches_algorithm(training, ALGORITHM)


class TestMaskablePPOOptimizeAndTrain:
    """RLMode.OPTIMIZE_AND_TRAIN: the search's best parameters go straight into
    a training run, without a trip through disk."""

    def test_optimize_and_train_produces_both_results(self):
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE_AND_TRAIN, ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            assert_search_results_saved(runner)
            assert_trained_model_saved(runner)
            assert_episode_was_played(runner)
            assert_shield_matches_algorithm(runner, ALGORITHM)


if __name__ == "__main__":
    run_all_tests(TestMaskablePPOHyperparameterSearch, TestMaskablePPOOptimizeAndTrain)
    print("\nAll MaskablePPO hyperparameter search smoke tests passed.")
