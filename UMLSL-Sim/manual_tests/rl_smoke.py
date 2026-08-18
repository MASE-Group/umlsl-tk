"""Scaffolding for the RL smoke tests: a whole RL run, shrunk to seconds.

The point of these tests is not that the agent learns anything -- it cannot, on
this budget -- but that every part of a run still fits together: the registries
hand back an algorithm and a reward profile, `EnvSpec` builds environments the
algorithm accepts, the callbacks fire, Optuna's trials finish, and the results
land on disk where `rl_io` says they will.

Three things have to be shrunk before that is a test rather than an experiment:

* **The budget.** `rl.constants` sizes a real run: a million timesteps, fifty
  Optuna trials. The runner reads those constants through its own module
  namespace (``from ... import TRAINING_TIMESTEPS``), so `rl_sandbox` rebinds
  them there. `OptunaSearch` instead takes its budget as constructor defaults,
  bound at import, so the sandbox swaps the class for a subclass that fixes
  them -- which is also how it forces the search in-process, since spawning
  worker processes per test would cost more than the trials do.
* **The world.** `CIRCUIT` with two NPCs is the smallest bundled scenario, and
  `EPISODE_STEPS` caps an episode at a fraction of `MAX_EPISODE_STEPS`.
* **Where results go.** `rl_io` anchors results at `src/umlsl_sim/rl_results`;
  the sandbox points them at a temporary directory instead, so a test run
  leaves nothing behind and each test sees an empty tree.

One thing is deliberately *not* shrunk: hyperparameters inside an Optuna trial
come from the real `sample_ppo_params`, so a trial can still draw
``n_steps=2048`` and run one full rollout past its budget. That is the
behaviour a search has, and a test that patched the sampler would not exercise
it.

Requires the optional RL extra (``pip install -e '.[rl]'``).
"""

import os
import shutil
import tempfile
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.rl import rl_io
from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.env_factory import EnvSpec
from umlsl_sim.rl.hyperparameters import optuna_search as optuna_search_module
from umlsl_sim.rl.hyperparameters.optuna_search import OptunaSearch
from umlsl_sim.rl.modes import RLMode
from umlsl_sim.rl.observations.observation_model_types import ObservationModelType
from umlsl_sim.rl.rewards.reward_types import RewardType
from umlsl_sim.rl.training import rl_runner as rl_runner_module
from umlsl_sim.rl.training.rl_runner import RLRunner
from umlsl_sim.scenario.loader import load_scenario

#: The smallest bundled scenario: four one-way roads round a single loop.
SCENARIO_KEY = "CIRCUIT"
#: NPCs besides the agent. Two is enough for the agent to meet traffic.
PLAYERS = 2

#: Steps before an episode is truncated. Small enough that an evaluation
#: episode costs a fraction of a second, large enough for the agent to move
#: through a crossing and for the shield to have something to mask.
EPISODE_STEPS = 25

#: Training budget of a smoke run, in environment steps.
TRAINING_TIMESTEPS = 64
#: Two evaluations per training run: enough for EvalCallback to checkpoint a
#: best model, which is the artefact the tests look for.
TRAINING_EVAL_FREQ = 32
TRAINING_EVAL_EPISODES = 1

#: Trials per search. Two is the smallest number that still exercises the
#: study's bookkeeping -- a second trial has a first one to be compared with.
OPTUNA_TRIALS = 2
OPTUNA_TRIAL_TIMESTEPS = 64
OPTUNA_TRIAL_EVALS = 2

#: PPO's defaults collect 2048 steps before the first policy update, which is
#: two orders of magnitude past a smoke run's budget. These keep the rollout
#: shorter than the run, so the update path is exercised rather than skipped.
#: Both PPO and MaskablePPO take them; the algorithms share a parameter space.
TINY_PPO_PARAMS: Dict[str, Any] = {"n_steps": 32, "batch_size": 8, "n_epochs": 1}

#: The observation model every test uses; there is currently only one.
OBSERVATION_MODEL = ObservationModelType.NUMERIC_OBSERVATION

#: Result id that `save_hyperparameters` files parameters under. A fixed
#: string rather than a timestamp: a test has to name it again when it asks a
#: runner to load them.
HYPERPARAMS_ID = "smoke-params"


class _SmokeSearch(OptunaSearch):
    """`OptunaSearch` with the budget a test can afford, in one process.

    The real class reads its budget from `rl.constants` as constructor
    *defaults*, evaluated at import, so rebinding the constants after the fact
    changes nothing. Subclassing is what a caller who cannot pass the arguments
    -- `RLRunner._optimize_hyperparams` builds the search itself -- is left
    with.
    """

    def __init__(self, rl_algorithm_type, env_spec, study_dir, **_budget_from_caller):
        super().__init__(
            rl_algorithm_type,
            env_spec,
            study_dir,
            n_trials=OPTUNA_TRIALS,
            timesteps_per_trial=OPTUNA_TRIAL_TIMESTEPS,
            trial_evals=OPTUNA_TRIAL_EVALS,
            # In-process: two trials are quicker than the interpreters that
            # would be spawned to share them. The parallel path has its own
            # test, which calls OptunaSearch directly.
            parallel_jobs=1,
        )


@contextmanager
def rl_sandbox() -> Iterator[str]:
    """Run RL code with test-sized budgets and results in a temporary tree.

    Yields:
        str: The temporary results root. `rl_io.RESULT_MODEL_PATH` and
            `RESULT_PARAM_PATH` point inside it for the duration, so a runner
            built in this block writes there.
    """
    results_root = tempfile.mkdtemp(prefix="umlsl_rl_smoke_")

    patches = {
        rl_io: {
            "RESULT_MODEL_PATH": os.path.join(results_root, "models"),
            "RESULT_PARAM_PATH": os.path.join(results_root, "hyperparameters"),
        },
        rl_runner_module: {
            "TRAINING_TIMESTEPS": TRAINING_TIMESTEPS,
            "TRAINING_EVAL_FREQ": TRAINING_EVAL_FREQ,
            "TRAINING_EVAL_EPISODES": TRAINING_EVAL_EPISODES,
            "MAX_EPISODE_STEPS": EPISODE_STEPS,
            # LOAD_TRAINED_MODEL is a demo rather than a training run and gets
            # a longer leash; a test watches for exactly as long as it trains.
            "DEMO_EPISODE_STEPS": EPISODE_STEPS,
        },
        optuna_search_module: {"OptunaSearch": _SmokeSearch},
    }

    saved = {module: {name: getattr(module, name) for name in names}
             for module, names in patches.items()}

    for module, names in patches.items():
        for name, value in names.items():
            setattr(module, name, value)

    try:
        yield results_root
    finally:
        for module, names in saved.items():
            for name, value in names.items():
                setattr(module, name, value)
        shutil.rmtree(results_root, ignore_errors=True)


def build_runner(
        rl_mode: RLMode,
        rl_algorithm_type: RLAlgorithmType,
        reward_type: RewardType,
        id_model: Optional[str] = None,
        id_hyperparams: Optional[str] = None,
        ) -> RLRunner:
    """An `RLRunner` on the smoke scenario, headless.

    Call inside `rl_sandbox`: the runner resolves its result paths and its
    episode cap in the constructor, so the patches have to be in place first.

    Args:
        rl_mode (RLMode): What the run should do.
        rl_algorithm_type (RLAlgorithmType): Which learner to build.
        reward_type (RewardType): Which reward profile to score by.
        id_model (Optional[str]): Saved-model id, for LOAD_TRAINED_MODEL.
        id_hyperparams (Optional[str]): Saved-parameter id, for TRAIN.

    Returns:
        RLRunner: Ready to `run()`.
    """
    scenario = load_scenario(SCENARIO_KEY)

    return RLRunner(
        roads=scenario["roads"],
        players=PLAYERS,
        render_mode=RenderMode.NO_GUI,
        show_reservation=False,
        scenario_name=scenario["scenario_name"],
        rl_mode=rl_mode,
        rl_algorithm_type=rl_algorithm_type,
        observation_model_type=OBSERVATION_MODEL,
        reward_type=reward_type,
        id_model=id_model,
        id_hyperparams=id_hyperparams,
        predefined_cars=scenario["predefined_cars"],
    )


def train_runner(rl_algorithm_type: RLAlgorithmType, reward_type: RewardType) -> RLRunner:
    """A TRAIN runner whose agent has been given `TINY_PPO_PARAMS`.

    The runner builds its algorithm with library defaults and only replaces
    them when it was asked to load saved hyperparameters, so a test that wants
    a short rollout has to say so here.
    """
    runner = build_runner(RLMode.TRAIN, rl_algorithm_type, reward_type)
    runner.rl_algorithm.change_params(TINY_PPO_PARAMS)
    return runner


def smoke_env_spec(reward_type: RewardType, uses_action_masks: bool) -> EnvSpec:
    """The `EnvSpec` behind `build_runner`, for tests that skip the runner."""
    scenario = load_scenario(SCENARIO_KEY)

    return EnvSpec(
        roads=scenario["roads"],
        players=PLAYERS,
        observation_model_type=OBSERVATION_MODEL,
        reward_type=reward_type,
        uses_action_masks=uses_action_masks,
        predefined_cars=scenario["predefined_cars"],
        render_mode=RenderMode.NO_GUI,
        show_reservation=False,
        max_episode_steps=EPISODE_STEPS,
    )


def save_hyperparameters(
        rl_algorithm_type: RLAlgorithmType,
        reward_type: RewardType,
        params: Optional[Dict[str, Any]] = None,
        id: str = HYPERPARAMS_ID,
        ) -> str:
    """Write a `best_params.parquet` where a TRAIN run would read one.

    Stands in for a finished search, so the loading half of `rl_io` can be
    tested without paying for the searching half.

    Args:
        rl_algorithm_type (RLAlgorithmType): Half of the path center: results
            are filed per configuration, and a runner only finds parameters
            saved under its own.
        reward_type (RewardType): The other half that varies here.
        params (Optional[Dict[str, Any]]): What to write; `TINY_PPO_PARAMS`
            by default.
        id (str): The result id to file them under.

    Returns:
        str: `id`, to hand to `build_runner` as `id_hyperparams`.
    """
    import pandas as pd

    path_center = rl_io.get_path_center(
        scenario=load_scenario(SCENARIO_KEY)["scenario_name"],
        rl_algo=rl_algorithm_type.name,
        obs_model=OBSERVATION_MODEL.name,
        reward_type=reward_type.name,
    )
    rl_io.save_best_params(
        pd.DataFrame([params if params else TINY_PPO_PARAMS]),
        rl_io.get_complete_path(path_center, id, False),
    )
    return id


def run_id(path: str) -> str:
    """The id (timestamp directory name) a runner filed its results under."""
    return os.path.basename(path)


def assert_trained_model_saved(runner: RLRunner) -> None:
    """EvalCallback must have checkpointed a model where `rl_io` expects one."""
    best_model = os.path.join(runner.model_path, rl_io.BEST_MODEL_FILE + ".zip")
    assert os.path.isfile(best_model), f"no best model at {best_model}"


def assert_search_results_saved(runner: RLRunner) -> None:
    """A finished search leaves the parameters and the trials behind it."""
    for filename in (rl_io.BEST_PARAMS_FILE, rl_io.TRIALS_FILE):
        path = os.path.join(runner.hyperparams_path, filename)
        assert os.path.isfile(path), f"no {filename} at {path}"


def best_params_of(runner: RLRunner) -> Dict[str, Any]:
    """Read back the parameters a finished OPTIMIZE run filed, as a later
    training run would -- through `rl_io`, not off the study in memory."""
    return rl_io.load_best_params(runner.path_center, run_id(runner.hyperparams_path))


def assert_episode_was_played(runner: RLRunner) -> None:
    """The run must have finished an episode and recorded how it ended."""
    episode_end = runner.env.unwrapped.episode_end

    assert episode_end is not None, "no episode finished on the run's environment"
    assert 0 < episode_end.steps <= EPISODE_STEPS
    assert episode_end.reason


def assert_shield_matches_algorithm(runner: RLRunner, rl_algorithm_type: RLAlgorithmType) -> None:
    """The shield is attached for masking algorithms and only for those.

    Which is the whole difference between the two shipped algorithms: PPO must
    learn safety from its reward, MaskablePPO never sees the unsafe actions.
    """
    from umlsl_sim.rl.algorithms.rl_algorithm_registry import get_rl_algo

    expected = get_rl_algo(rl_algorithm_type).requires_action_masks

    assert runner.uses_action_masks is expected
    assert (runner.action_shield is not None) is expected
    assert (runner.env.unwrapped.action_shield is not None) is expected

    if expected:
        assert runner.action_shield.stats()["steps"] > 0, "shield masked nothing"


def run_all_tests(*test_classes) -> None:
    """Run the test classes of a module as a script, as `manual_tests` does."""
    for test_class in test_classes:
        instance = test_class()
        for name in sorted(n for n in dir(instance) if n.startswith("test_")):
            getattr(instance, name)()
            print(f"{test_class.__name__}.{name} passed")
