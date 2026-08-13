import datetime

from typing import TYPE_CHECKING, List, Callable, Dict, Tuple
from umlsl_sim.simulation.controllers.abstract_simulation_controller import AbstractGameController
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.simulation.episode_history import GameHistory
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import ObservationModelType
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.abstract_observation import Observation
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm import RLAlgorithm
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_registry import get_rl_algo
from umlsl_sim.reinforcement_learning.algorithms.sample_ppo_params import constrain_ppo_params
from umlsl_sim.reinforcement_learning.env_factory import EnvSpec
from umlsl_sim.reinforcement_learning.rl_constants import (
    TRAINING_TIMESTEPS,
    TRAINING_EVAL_FREQ,
    TRAINING_EVAL_EPISODES,
)
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
from umlsl_sim.reinforcement_learning.rl_io import get_path_center, get_complete_path, load_best_params, load_best_model, save_best_params, save_study_materials, load_game_history
from umlsl_sim.scenario_io.car_spec import CarSpec

# Heavy ML/optimization deps are imported lazily inside the methods that need
# them (training, evaluation, hyperparameter search). This lets non-RL parts
# of the codebase import this module without paying the optuna/sb3 cost.
if TYPE_CHECKING:
    import optuna  # noqa: F401

class RLGameController(AbstractGameController):
    mode_handlers: Dict[RLMode, Callable] = {}

    def __init__(
            self,
            roads: List[Road], 
            players: int,
            render_mode: RenderMode,
            show_reservation: bool,
            scenario_name: str, 
            rl_mode: RLMode, 
            rl_algorithm_type: RLAlgorithmType,
            observation_model_type: ObservationModelType,
            reward_type: RewardType,
            id_model: None | str = None,
            id_history: None | str = None,
            id_hyperparams: None | str = None,
            predefined_cars: None | List[CarSpec] = None,
            ):

            super().__init__(roads, players, render_mode, show_reservation)
            self.scenario_name = scenario_name

            self.id_history = id_history

            self.rl_mode = rl_mode
            self.rl_algorithm_type = rl_algorithm_type
            self.observation_model_type = observation_model_type
            self.reward_type = reward_type
            self.id_model = id_model
            self.id_hyperparams = id_hyperparams

            self.path_center = get_path_center(
                scenario=self.scenario_name,
                rl_algo=self.rl_algorithm_type.name,
                obs_model=self.observation_model_type.name,
                reward_type=self.reward_type.name,
            )
            self.model_path = get_complete_path(self.path_center, str(datetime.datetime.now().replace(microsecond=0)), True)
            self.hyperparams_path = get_complete_path(self.path_center, str(datetime.datetime.now().replace(microsecond=0)), False)

            rl_algo_class: RLAlgorithm = get_rl_algo(self.rl_algorithm_type)

            # Masking algorithms drive the safety shield: unsafe actions are
            # removed before the agent acts, rather than penalised afterwards
            # by the reward. The spec carries this flag so that every
            # environment built from it -- training, evaluation, one per
            # hyperparameter trial -- gets the same shield.
            self.uses_action_masks: bool = rl_algo_class.requires_action_masks

            # The recipe, kept so evaluation and the hyperparameter search can
            # build their own environments instead of borrowing this one.
            self.env_spec = EnvSpec(
                roads=self.roads,
                players=self.players,
                observation_model_type=self.observation_model_type,
                reward_type=self.reward_type,
                uses_action_masks=self.uses_action_masks,
                predefined_cars=list(predefined_cars) if predefined_cars else [],
                rl_mode=self.rl_mode,
                render_mode=self.render_mode,
                show_reservation=self.show_reservation,
            )

            # Monitor-wrapped, so episode reward, length and time are recorded.
            self.env, self.action_shield = self.env_spec.build()

            self.game_model: TrafficEnv = self.env.unwrapped.game_model
            self.observation_model: Observation = self.env.unwrapped.observation_model

            self.rl_algorithm: RLAlgorithm = rl_algo_class(self.env)


    def run(self) -> None:
        handler = self.mode_handlers.get(self.rl_mode)
        if handler:
            handler(self)
        elif self.render_mode.value:
            self.frame_count = 0
            self._run_gui()    
        else:
            self._run_no_gui()

        self.game_model.current_state()


    def register_mode(mode_handlers, mode) -> Callable[[Callable], Callable]:
        def decorator(func) -> Callable:
            mode_handlers[mode] = func
            return func
        return decorator


    """
    To add new reinforcement learning modes create a new RLMode Enum (e.g. RLMode.example)
    and a new function in this class (e.g. def _example_fnc(self)). Use the register_mode function
    to add the function to the mode_handlers dictionary. The function then should look like this:

    @register_mode(mode_handlers, RLMode.example)
    def _example_fnc(self):

    """

    def _eval_helpers(self) -> Tuple[Callable, Callable]:
        """Return the (EvalCallback, evaluate_policy) pair matching the
        algorithm. Masked policies need the sb3-contrib variants, which pass
        the environment's action masks into every prediction; using the plain
        ones would evaluate the policy without its shield."""
        if self.uses_action_masks:
            from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback
            from sb3_contrib.common.maskable.evaluation import evaluate_policy

            return MaskableEvalCallback, evaluate_policy

        from stable_baselines3.common.callbacks import EvalCallback
        from stable_baselines3.common.evaluation import evaluate_policy

        return EvalCallback, evaluate_policy

    def _log_shield_stats(self) -> None:
        """Print what the shield did, when there is one."""
        if self.action_shield is None:
            return
        stats = self.action_shield.stats()
        print(
            f"Safety shield: {stats['steps']:.0f} masked steps, "
            f"{stats['mean_allowed_actions']:.1f} of {stats['total_actions']:.0f} "
            f"actions allowed on average, "
            f"{stats['forced_brake_steps']:.0f} steps braking-only, "
            f"{stats['empty_mask_steps']:.0f} empty masks."
        )

    @register_mode(mode_handlers, RLMode.TRAIN) # _train_model = register_mode(mode_handlers, RLMode.TRAIN)(_train_model)
    def _train_model(self):
        from stable_baselines3.common.callbacks import CallbackList

        EvalCallback, evaluate_policy = self._eval_helpers()

        from umlsl_sim.reinforcement_learning.gymnasium_env.callbacks.game_history_callback import GameHistoryCallback

        if self.id_hyperparams != None:
            hyperparams = load_best_params(self.path_center, self.id_hyperparams)
            self.rl_algorithm.change_params(hyperparams)

        # Evaluation runs in its own world. Sharing the training environment
        # would make each evaluation reset the episode the agent is currently
        # collecting a rollout from; it is also headless, since nobody is
        # watching a background evaluation and a second window would only
        # compete with the training one.
        eval_env, _ = self.env_spec.headless().build()

        # Used to save the best model
        eval_callback = EvalCallback(eval_env,
                                     best_model_save_path=self.model_path,
                                     eval_freq=TRAINING_EVAL_FREQ,
                                     n_eval_episodes=TRAINING_EVAL_EPISODES,
                                     render=False)

        history_callback = GameHistoryCallback(self.env.unwrapped, self.model_path)

        try:
            # Train the agent
            self.rl_algorithm.algorithm.learn(total_timesteps=TRAINING_TIMESTEPS, callback=CallbackList([eval_callback, history_callback]), progress_bar=True)
        finally:
            eval_env.close()

        evaluate_policy(self.rl_algorithm.algorithm, self.env, n_eval_episodes=1, render=self.render_mode.value)

        self._log_shield_stats()


    @register_mode(mode_handlers, RLMode.LOAD_TRAINED_MODEL)
    def _load_model(self):
        _, evaluate_policy = self._eval_helpers()

        model = load_best_model(self.path_center, self.id_model, self.rl_algorithm, self.env)
        evaluate_policy(model, self.env, n_eval_episodes=1, render=self.render_mode.value)

        self._log_shield_stats()


    @register_mode(mode_handlers, RLMode.LOAD_HISTORY)
    def _load_history(self):
        if self.id_history is not None:
            map_history, car_history, action_history = load_game_history(self.path_center, self.id_model, self.id_history)

            game_history = GameHistory()
            game_history.set_map(map_history)
            game_history.set_list_of_cars(car_history)
            game_history.set_action_history_dict(action_history)

            game_history.history_playback(False)
            # play history_playback


    @register_mode(mode_handlers, RLMode.OPTIMIZE)
    def _optimize_hyperparams(self):
        import pandas as pd

        from umlsl_sim.reinforcement_learning.hyperparameters.optuna_search import OptunaSearch

        # The search builds its own environment per trial (and per worker
        # process), so it takes the recipe rather than this controller's
        # already-running environment.
        optuna_search = OptunaSearch(
            rl_algorithm_type=self.rl_algorithm_type,
            env_spec=self.env_spec.headless(),
            study_dir=self.hyperparams_path,
        )
        study = optuna_search.search_params()

        best_params = study.best_params.copy()
        best_params.pop("lr_schedule")
        # study.best_params returns the values Optuna originally suggested, not the
        # post-correction ones used inside the trial. Re-apply the PPO constraint
        # so the saved/loaded best_params don't trigger SB3's truncated mini-batch warning.
        best_params = constrain_ppo_params(best_params)

        best_params_df = pd.DataFrame([best_params])
        save_best_params(best_params_df, self.hyperparams_path)
        save_study_materials(study, self.hyperparams_path)

        return best_params


    @register_mode(mode_handlers, RLMode.OPTIMIZE_AND_TRAIN)
    def _optimize_and_train(self):
        best_params = self._optimize_hyperparams()

        self.rl_algorithm.change_params(best_params)
        self.id_hyperparams = None # needed if id_hyperparams parameter is not None
        self._train_model()
        