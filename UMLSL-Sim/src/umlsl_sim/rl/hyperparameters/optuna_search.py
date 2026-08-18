import os
from functools import partial
from typing import TYPE_CHECKING, Any, Dict

from umlsl_sim.rl.algorithms.rl_algorithm_registry import get_rl_algo
from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.env_factory import EnvSpec
from umlsl_sim.rl.constants import (
    HYPERPARAMS_TRAINING_TIMESTEPS,
    OPTUNA_PARALLEL_JOBS,
    OPTUNA_PRUNER_STARTUP_TRIALS,
    OPTUNA_PRUNER_WARMUP_EVALS,
    OPTUNA_TRIAL_EVALS,
    OPTUNA_TRIALS,
)

# optuna and stable_baselines3 are heavy deps imported lazily inside the
# methods that need them, so this module can be imported by lighter tools
# (e.g. tests that monkey-patch search_params) without paying that cost.
if TYPE_CHECKING:
    import optuna
    from optuna.study import Study

STUDY_NAME = "umlsl_hyperparameter_search"
STUDY_STORAGE_FILE = "study.log"


class OptunaSearch:
    """Hyperparameter optimization using Optuna.

    Automatically finds the best hyperparameters for an RL algorithm by training
    multiple agents with different settings and evaluating their performance.

    ## How It Works

    1. Create a study (optimization problem)
    2. For each trial (iteration):
        a. Sample hyperparameters intelligently
        b. Build a fresh environment and agent for this trial
        c. Train briefly, evaluating OPTUNA_TRIAL_EVALS times along the way
        d. Report each evaluation to the pruner, which may abandon the trial
        e. Return the best score the trial reached
    3. Return hyperparameters from best-performing trial

    ## Optuna Components

    - **Sampler**: Smart hyperparameter selection strategy
        - TPESampler: Tree-structured Parzen Estimator (learns from previous trials)
    - **Pruner**: Early stopping of unpromising trials
        - MedianPruner: Stops if worse than median performance so far
    - **Study**: The optimization session (collection of trials)
    - **Trial**: One training run with specific hyperparameters

    ## Isolation

    Every trial builds its own environment from `env_spec`, plus a second one
    for evaluation. Trials therefore share no simulation state, and no
    evaluation ever resets the environment a rollout is being collected from --
    which is also what makes it safe to run several trials at once.

    ## Parallelism

    With OPTUNA_PARALLEL_JOBS > 1 the trials run in separate processes against a
    study shared through file storage under `study_dir`. Processes rather than
    threads because the simulation is pure Python: threads would serialise on
    the GIL and buy nothing. Each worker samples from the shared history, so the
    TPE surrogate and the pruner still see every finished trial.

    ## Output

    Returns an `optuna.Study` object containing:
    - Best hyperparameters found
    - Performance of each trial
    - Parameter importance analysis

    ## Configuration

    See `rl/constants.py`:
    - HYPERPARAMS_TRAINING_TIMESTEPS: Steps per trial (lower = faster but less reliable)
    - OPTUNA_TRIALS: Number of trials to run
    - OPTUNA_TRIAL_EVALS: Evaluations (and pruning decisions) per trial
    - OPTUNA_PARALLEL_JOBS: Trials to run concurrently, one process each
    """

    def __init__(
            self,
            rl_algorithm_type: RLAlgorithmType,
            env_spec: EnvSpec,
            study_dir: str,
            n_trials: int = OPTUNA_TRIALS,
            timesteps_per_trial: int = HYPERPARAMS_TRAINING_TIMESTEPS,
            trial_evals: int = OPTUNA_TRIAL_EVALS,
            parallel_jobs: int = OPTUNA_PARALLEL_JOBS,
            ):
        """Initialize the hyperparameter search.

        The budget is held on the instance, not read from `rl.constants` at the
        point of use: worker processes are started fresh and would otherwise
        re-read the module defaults, silently ignoring a caller that asked for a
        shorter search.

        Args:
            rl_algorithm_type (RLAlgorithmType): Which algorithm to optimize.
                Taken as a type rather than an instance because every trial
                builds its own agent, possibly in another process.
            env_spec (EnvSpec): Recipe for the environments the trials train and
                evaluate on. Should be headless.
            study_dir (str): Directory for the shared study storage. Also where
                the caller writes the study's results, so a completed search
                stays next to the parameters it produced.
            n_trials (int): Total trials for the whole study, however many
                processes share the work.
            timesteps_per_trial (int): Training budget of a single trial.
            trial_evals (int): Evaluations per trial; sets both eval_freq and
                how many chances the pruner gets to judge a trial.
            parallel_jobs (int): Worker processes; 1 runs in-process.
        """
        self.rl_algorithm_type = rl_algorithm_type
        self.env_spec = env_spec
        self.study_dir = study_dir
        self.n_trials = n_trials
        self.timesteps_per_trial = timesteps_per_trial
        self.trial_evals = trial_evals
        self.parallel_jobs = parallel_jobs

    # ------------------------------------------------------------- study ----

    def _storage(self) -> "optuna.storages.BaseStorage":
        """File-backed storage, so worker processes share one study.

        JournalStorage rather than SQLite: it is Optuna's recommended backend
        for several processes appending concurrently.
        """
        from optuna.storages import JournalStorage
        from optuna.storages.journal import JournalFileBackend

        os.makedirs(self.study_dir, exist_ok=True)
        return JournalStorage(JournalFileBackend(os.path.join(self.study_dir, STUDY_STORAGE_FILE)))

    def _create_study(self) -> "Study":
        """Create (or reattach to) the study this search writes into."""
        import optuna
        from optuna.pruners import MedianPruner
        from optuna.samplers import TPESampler

        return optuna.create_study(
            study_name=STUDY_NAME,
            storage=self._storage(),
            load_if_exists=True,
            sampler=TPESampler(n_startup_trials=10, multivariate=True),
            # n_warmup_steps counts the intermediate values reported by
            # TrialEvalCallback, i.e. evaluations -- keep it well below
            # OPTUNA_TRIAL_EVALS or nothing is ever pruned.
            pruner=MedianPruner(
                n_startup_trials=OPTUNA_PRUNER_STARTUP_TRIALS,
                n_warmup_steps=OPTUNA_PRUNER_WARMUP_EVALS,
            ),
            direction="maximize",  # Maximize mean reward
        )

    def search_params(self) -> "Study":
        """Execute the hyperparameter optimization search.

        Runs `n_trials` trials -- sequentially, or `parallel_jobs` at a time in
        separate processes -- and returns the finished study.

        Returns:
            Study: Optuna study object containing:
                - best_params: Dict of best hyperparameters found
                - best_value: Best performance score (mean reward)
                - trials_dataframe(): DataFrame with all trial results
                - For visualization, use plot_optimization_history(study), etc.
        """
        import optuna

        # Trial results are printed by _report_trial in a single line each;
        # Optuna's own INFO log would say the same thing twice.
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        study = self._create_study()

        if self.parallel_jobs <= 1:
            study.optimize(self.objective, n_trials=self.n_trials,
                           callbacks=[partial(_report_trial, n_trials=self.n_trials)])
            return study

        self._search_in_parallel()

        # Re-read the study so it carries the trials the workers wrote.
        return self._create_study()

    def _search_in_parallel(self) -> None:
        """Run the trials in `parallel_jobs` worker processes.

        Each worker keeps pulling trials until the study as a whole has
        `n_trials` finished ones, so a worker that draws slow hyperparameters
        simply completes fewer trials than its siblings.
        """
        import multiprocessing

        # Spawn, not fork: torch and fork are a known deadlock combination, and
        # spawn is the only start method available on macOS anyway.
        ctx = multiprocessing.get_context("spawn")

        # More workers than trials would just be processes that start, find the
        # study already full, and exit.
        jobs = min(self.parallel_jobs, self.n_trials)

        workers = [
            ctx.Process(
                target=_worker_optimize,
                args=(self.rl_algorithm_type, self.env_spec, self.study_dir,
                      self.n_trials, self.timesteps_per_trial, self.trial_evals,
                      self.parallel_jobs),
                name=f"optuna-worker-{i}",
                daemon=False,
            )
            for i in range(jobs)
        ]

        print(f"Hyperparameter search: {self.n_trials} trials across "
              f"{jobs} worker processes.")

        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        failed = [w.name for w in workers if w.exitcode not in (0, None)]
        if failed:
            # Trials already written to storage survive, so this is a warning
            # about lost capacity rather than a lost search.
            print(f"Warning: worker(s) {', '.join(failed)} exited abnormally; "
                  f"the study kept the trials they had finished.")

    # ------------------------------------------------------------ trials ----

    def objective(self, trial: "optuna.Trial") -> float:
        """Objective function for a single Optuna trial.

        This function is called for each trial. It samples hyperparameters, trains
        the agent, and returns the evaluation score. Optuna uses the returned value
        to decide which hyperparameters are better.

        Args:
            trial (optuna.Trial): The current Optuna trial. Used to suggest hyperparameters.

        Returns:
            float: The best mean reward the trial reached (higher is better).

        Raises:
            optuna.TrialPruned: If the pruner judged the trial hopeless against
                the trials finished so far.

        Workflow:
            1. Build a training and an evaluation environment for this trial
            2. Sample hyperparameters and build the agent with them
            3. Train for `timesteps_per_trial`, evaluating along the way
            4. Report every evaluation to the pruner
            5. Return the best mean reward
        """
        import optuna
        from stable_baselines3.common.callbacks import StopTrainingOnNoModelImprovement

        rl_algo_class = get_rl_algo(self.rl_algorithm_type)

        train_env, _ = self.env_spec.build()
        eval_env, _ = self.env_spec.build()

        try:
            rl_algorithm = rl_algo_class(train_env)
            sampled_hyperparams: Dict[str, Any] = rl_algorithm.get_sample_params(trial)
            rl_algorithm.change_params(sampled_hyperparams)
            model = rl_algorithm.algorithm

            # eval_freq must leave room for several evaluations within the
            # trial's budget, otherwise StopTrainingOnNoModelImprovement never
            # reaches min_evals and the callback is effectively dead code.
            eval_freq = max(1, self.timesteps_per_trial // self.trial_evals)
            stop_callback = StopTrainingOnNoModelImprovement(max_no_improvement_evals=5, min_evals=5, verbose=1)
            # n_eval_episodes=1 keeps eval cheap; episodes can still be long even with
            # the MAX_EPISODE_STEPS cap in MlslEnv.
            eval_callback = _trial_eval_callback(rl_algo_class.requires_action_masks)(
                eval_env,
                trial=trial,
                callback_after_eval=stop_callback,
                eval_freq=eval_freq,
                n_eval_episodes=1,
                render=False,
            )

            model.learn(
                total_timesteps=self.timesteps_per_trial,
                callback=eval_callback,
                # Several workers writing progress bars to one terminal produce
                # nothing readable; they report per finished trial instead.
                progress_bar=self.parallel_jobs <= 1,
            )

            if eval_callback.is_pruned:
                raise optuna.TrialPruned()

            return eval_callback.best_mean_reward
        finally:
            train_env.close()
            eval_env.close()


def _trial_eval_callback(requires_action_masks: bool):
    """Build the EvalCallback subclass that reports to Optuna's pruner.

    Pruning needs the trial's score *while it is still running*: an
    EvalCallback already computes exactly that score at every evaluation, so
    this subclass forwards it to the trial and stops training as soon as the
    pruner rules the trial out.

    Args:
        requires_action_masks (bool): Whether the algorithm consumes action
            masks. A masked policy must be evaluated with its mask, or the
            search would score every trial against a shield-less policy it
            never trained.

    Returns:
        type: An EvalCallback subclass taking an extra `trial` argument and
            exposing `is_pruned`.
    """
    if requires_action_masks:
        from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback as base_callback
    else:
        from stable_baselines3.common.callbacks import EvalCallback as base_callback

    class TrialEvalCallback(base_callback):
        def __init__(self, eval_env, trial: "optuna.Trial", **kwargs):
            super().__init__(eval_env, **kwargs)
            self.trial = trial
            self.eval_idx = 0
            self.is_pruned = False

        def _on_step(self) -> bool:
            continue_training = super()._on_step()

            # super() only evaluates on its own schedule; report exactly when
            # it has produced a fresh number.
            if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:
                self.eval_idx += 1
                self.trial.report(self.last_mean_reward, self.eval_idx)
                if self.trial.should_prune():
                    self.is_pruned = True
                    return False

            return continue_training

    return TrialEvalCallback


def _stop_when_study_is_full(study: "Study", trial: "optuna.trial.FrozenTrial", n_trials: int) -> None:
    """Stop this worker once the study as a whole has enough trials.

    The budget belongs to the study, not to any one worker, so workers take
    trials as they free up rather than being handed fixed shares -- a worker
    that draws cheap (or pruned) hyperparameters simply does more of them.

    Trials still RUNNING in sibling workers count towards the total. Optuna's
    own MaxTrialsCallback counts only finished ones, which lets every worker
    start one more trial before it notices the study is full: with 4 workers
    and a 4-trial budget that measured 7 trials instead of 4.
    """
    from optuna.trial import TrialState

    in_flight_or_done = study.get_trials(
        deepcopy=False,
        states=(TrialState.COMPLETE, TrialState.PRUNED, TrialState.RUNNING),
    )
    if len(in_flight_or_done) >= n_trials:
        study.stop()


def _report_trial(study: "Study", trial: "optuna.trial.FrozenTrial", n_trials: int) -> None:
    """Print one line per finished trial, so progress is legible with the
    per-trial progress bars switched off."""
    from optuna.trial import TrialState

    finished = len([t for t in study.trials if t.state in (TrialState.COMPLETE, TrialState.PRUNED)])
    value = f"value={trial.value:.3f}" if trial.value is not None else "no value"
    print(f"[optuna] trial {finished}/{n_trials} {trial.state.name.lower()} ({value})")


def _worker_optimize(
        rl_algorithm_type: RLAlgorithmType,
        env_spec: EnvSpec,
        study_dir: str,
        n_trials: int,
        timesteps_per_trial: int,
        trial_evals: int,
        parallel_jobs: int,
        ) -> None:
    """Worker-process entry point: pull trials until the study is full.

    Module-level (and taking only picklable arguments) because the "spawn" start
    method has to import and call it in a fresh interpreter.
    """
    import optuna
    import torch

    # One intra-op thread per worker: with parallel_jobs processes each
    # defaulting to every core, the workers would fight over the machine.
    torch.set_num_threads(1)
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    search = OptunaSearch(
        rl_algorithm_type, env_spec, study_dir,
        n_trials=n_trials,
        timesteps_per_trial=timesteps_per_trial,
        trial_evals=trial_evals,
        # Carried through so the trials know they are sharing the terminal with
        # sibling workers and keep their progress bars to themselves.
        parallel_jobs=parallel_jobs,
    )
    study = search._create_study()
    study.optimize(
        search.objective,
        n_trials=n_trials,
        callbacks=[
            partial(_stop_when_study_is_full, n_trials=n_trials),
            partial(_report_trial, n_trials=n_trials),
        ],
    )
