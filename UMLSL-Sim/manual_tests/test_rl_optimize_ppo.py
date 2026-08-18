"""Smoke tests: Optuna hyperparameter search for PPO, on both reward profiles.

A search is the part of the RL stack with the most machinery between the ask
and the answer -- a study, a sampler, a pruner, one environment per trial, an
`EvalCallback` subclass reporting into the trial, and worker processes if it is
allowed them. These tests run all of it on two trials of 64 timesteps each, so
what they can show is that the machinery turns over: trials finish, the study
records them, the best parameters come back constrained and are written where a
later training run will read them.

The searched space is the real `sample_ppo_params`, not a shrunken stand-in, so
a trial may still draw ``n_steps=2048`` and collect one rollout well past its
budget -- exactly as a production search does.

Requires the optional RL extra (``pip install -e '.[rl]'``).

Usage:
    pytest manual_tests/test_rl_optimize_ppo.py -v
    python manual_tests/test_rl_optimize_ppo.py
"""

import os

import pandas as pd

from rl_smoke import (
    OPTUNA_TRIALS,
    OPTUNA_TRIAL_EVALS,
    OPTUNA_TRIAL_TIMESTEPS,
    assert_episode_was_played,
    assert_search_results_saved,
    assert_trained_model_saved,
    best_params_of,
    build_runner,
    rl_sandbox,
    run_all_tests,
    run_id,
    smoke_env_spec,
)

from umlsl_sim.rl import rl_io
from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.modes import RLMode
from umlsl_sim.rl.rewards.reward_types import RewardType

ALGORITHM = RLAlgorithmType.PPO

#: Parameters `sample_ppo_params` returns for every trial. The saved parquet
#: has to carry them all, or a training run loading it gets a different agent
#: from the one the search scored.
EXPECTED_PARAMS = {
    "n_steps", "batch_size", "gamma", "learning_rate", "ent_coef",
    "clip_range", "n_epochs", "gae_lambda", "max_grad_norm", "vf_coef",
}


class TestPPOHyperparameterSearch:
    """RLMode.OPTIMIZE, once per reward profile."""

    def test_searches_with_the_initial_reward(self):
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            assert_search_results_saved(runner)

    def test_searches_with_the_safety_aware_reward(self):
        """Trials are scored by the reward profile, so a search is per-profile
        and its results are filed under one."""
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            runner.run()

            assert_search_results_saved(runner)
            assert RewardType.SAFETY_AWARE_REWARD.name in runner.hyperparams_path

    def test_best_params_are_complete_and_constrained(self):
        """What the search files is what a training run gets.

        Two things are easy to get wrong here and are checked rather than
        assumed: `lr_schedule` is a sampling instruction, not a PPO argument,
        and has to be gone by the time anything loads the parquet; and Optuna
        stores the values it *suggested*, so the batch_size <= n_steps
        correction has to be re-applied before saving or SB3 truncates a
        mini-batch on every update of the run that loads them.
        """
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            best_params = best_params_of(runner)

            assert EXPECTED_PARAMS <= set(best_params)
            assert "lr_schedule" not in best_params
            assert best_params["batch_size"] <= best_params["n_steps"]

    def test_study_records_every_trial(self):
        """The trials CSV is the record of the search, and the pruner's
        decisions are only legible through it."""
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE, ALGORITHM, RewardType.INITIAL_REWARD)
            runner.run()

            trials = pd.read_csv(os.path.join(runner.hyperparams_path, rl_io.TRIALS_FILE))

            assert len(trials) == OPTUNA_TRIALS
            assert set(trials["state"]) <= {"COMPLETE", "PRUNED"}

    def test_search_output_is_loadable_by_training(self):
        """The full hand-off: search, then train from what it wrote.

        Worth its own test because the parameters make a round trip through
        parquet, which is where a value can come back as a numpy dtype PPO
        will not take, or not come back at all.
        """
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

            best_params = best_params_of(search)

            # Regression guard: parquet stores one row, and reading it back as
            # a row would make every integer a float -- which PPO refuses.
            assert isinstance(best_params["n_steps"], int)
            assert training.rl_algorithm.algorithm.n_steps == best_params["n_steps"]
            assert_episode_was_played(training)
            assert_trained_model_saved(training)


class TestPPOOptimizeAndTrain:
    """RLMode.OPTIMIZE_AND_TRAIN: one run that does both, in memory."""

    def test_optimize_and_train_produces_both_results(self):
        with rl_sandbox():
            runner = build_runner(RLMode.OPTIMIZE_AND_TRAIN, ALGORITHM, RewardType.SAFETY_AWARE_REWARD)
            runner.run()

            assert_search_results_saved(runner)
            assert_trained_model_saved(runner)
            assert_episode_was_played(runner)


class TestParallelSearch:
    """The search's other half: trials shared between worker processes.

    Driven through `OptunaSearch` directly rather than through the runner,
    which always takes the budget the sandbox forces on it -- and this is the
    one test that wants a different one.
    """

    def test_workers_share_one_study(self):
        import tempfile

        from umlsl_sim.rl.hyperparameters.optuna_search import OptunaSearch

        with tempfile.TemporaryDirectory(prefix="umlsl_rl_smoke_study_") as study_dir:
            search = OptunaSearch(
                rl_algorithm_type=ALGORITHM,
                env_spec=smoke_env_spec(RewardType.INITIAL_REWARD, uses_action_masks=False),
                study_dir=study_dir,
                n_trials=OPTUNA_TRIALS,
                timesteps_per_trial=OPTUNA_TRIAL_TIMESTEPS,
                trial_evals=OPTUNA_TRIAL_EVALS,
                parallel_jobs=2,
            )
            study = search.search_params()

            # The budget belongs to the study, not to each worker: two workers
            # asked for two trials must finish two, not two each.
            assert len(study.trials) == OPTUNA_TRIALS
            assert study.best_params
            # File-backed storage is what let the workers see each other.
            assert os.path.isfile(os.path.join(study_dir, "study.log"))


if __name__ == "__main__":
    run_all_tests(TestPPOHyperparameterSearch, TestPPOOptimizeAndTrain, TestParallelSearch)
    print("\nAll PPO hyperparameter search smoke tests passed.")
