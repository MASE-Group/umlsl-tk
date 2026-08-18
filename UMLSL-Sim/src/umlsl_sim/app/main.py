"""Assembles a run: scenario description in, a finished simulation out.

`main()` is the one place that chooses between the two runners -- plain NPC
traffic (`umlsl_sim.runners.ScenarioRunner`) and reinforcement learning
(`umlsl_sim.rl.training.RLRunner`) -- and it chooses on `rl_mode` alone. Its
keyword arguments are exactly what `umlsl_sim.scenario.load_scenario` returns
plus the run options, so

    main(**load_scenario("two_crossings"), render_mode=RenderMode.GUI,
         show_reservation=True)

is the whole interface. Importing this module goes through `umlsl_sim.app`,
which binds the renderer and the default car controller before anything runs.

The RL imports are optional: without the `[rl]` extra they fail, `main()` still
works for plain simulations, and asking for an `rl_mode` raises with the install
command.
"""
# Deferred annotations: main()'s signature names the RL types, which are only
# importable when the optional [rl] extra is installed. Without this, defining
# main() raises NameError on a non-RL install (Python < 3.14).
from __future__ import annotations

import logging
from typing import List

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s')

from umlsl_sim.scenario.loader import load_scenario
from umlsl_sim.factories.car_spec import CarSpec
from umlsl_sim.runners.runner import SimulationRunner
from umlsl_sim.runners.scenario_runner import ScenarioRunner
from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.rl.modes import RLMode
RL_IMPORT_ERROR: None | ImportError = None
try:
    from umlsl_sim.rl.training.rl_runner import RLRunner
    from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
    from umlsl_sim.rl.observations.observation_model_types import ObservationModelType
    from umlsl_sim.rl.rewards.reward_types import RewardType
except ImportError as exc:
    RL_IMPORT_ERROR = exc
    logging.warning("Reinforcement learning imports failed.", exc_info=True)

def main(
        scenario_name,
        roads,
        players,
        render_mode: RenderMode,
        show_reservation: bool,
        rl_mode: None | RLMode = None,
        rl_algorithm_type: RLAlgorithmType | None = None,
        observation_model_type: ObservationModelType | None = None,
        reward_type: RewardType | None = None,
        id_model: None | str = None,
        id_history: None | str = None,
        id_hyperparams: None | str = None,
        predefined_cars: None | List[CarSpec] = None,
        ):

    if not rl_mode:
        runner: SimulationRunner = ScenarioRunner(
            roads,
            players,
            render_mode,
            show_reservation,
            predefined_cars=predefined_cars,
        )
    else:
        if RL_IMPORT_ERROR is not None:
            raise RuntimeError(
                f"rl_mode={rl_mode} was requested but the reinforcement-learning "
                f"stack is not available ({RL_IMPORT_ERROR}). Install the optional "
                f"extra with:  pip install -e '.[rl]'"
            ) from RL_IMPORT_ERROR
        runner: SimulationRunner = RLRunner(
            roads,
            players,
            render_mode,
            show_reservation,
            scenario_name,
            rl_mode,
            rl_algorithm_type,
            observation_model_type,
            reward_type,
            id_model,
            id_history,
            id_hyperparams,
            predefined_cars=predefined_cars,
        )

    runner.run()

if __name__ == '__main__':

    scenario = load_scenario("TWO_CROSSINGS")

    # Plain simulation: NPC cars driven by the A* controller, no RL involved.
    # This is the default because it needs no trained model and no [rl] extra.
    main(**scenario, render_mode=RenderMode.GUI, show_reservation=True)

    # --- Reinforcement-learning variants ------------------------------------
    # Uncomment one of these instead. They need the [rl] extra installed, and
    # the LOAD_* modes need an `id_*` that actually exists under rl_results/ —
    # see UMLSL-Sim/README.md, "Finding Model/History IDs".

    # Train an agent from scratch, with safety left to the reward:
    # main(
    #     **scenario,
    #     render_mode=RenderMode.NO_GUI,
    #     show_reservation=False,
    #     rl_mode=RLMode.TRAIN,
    #     rl_algorithm_type=RLAlgorithmType.PPO,
    #     observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    #     reward_type=RewardType.SAFETY_AWARE_REWARD,
    # )

    # The same, with the safety shield instead: unsafe actions are masked out
    # before the agent acts, so the reward only has to score the objective.
    # main(
    #     **scenario,
    #     render_mode=RenderMode.NO_GUI,
    #     show_reservation=False,
    #     rl_mode=RLMode.OPTIMIZE_AND_TRAIN,
    #     rl_algorithm_type=RLAlgorithmType.MASKABLE_PPO,
    #     observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    #     reward_type=RewardType.INITIAL_REWARD,
    # )
    # Watch a previously trained agent. The safety shield is on for the whole
    # run, because MASKABLE_PPO is what the model was trained with:
    # main(
    #     **scenario,
    #     render_mode=RenderMode.GUI,
    #     show_reservation=True,
    #     rl_mode=RLMode.LOAD_TRAINED_MODEL,
    #     rl_algorithm_type=RLAlgorithmType.MASKABLE_PPO,
    #     observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    #     reward_type=RewardType.INITIAL_REWARD,
    #     id_model="2026-08-13 12:01:02",   # replace with your model timestamp
    # )

    # The same for a reward-trained agent:
    # main(
    #     **scenario,
    #     render_mode=RenderMode.GUI,
    #     show_reservation=True,
    #     rl_mode=RLMode.LOAD_TRAINED_MODEL,
    #     rl_algorithm_type=RLAlgorithmType.PPO,
    #     observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    #     reward_type=RewardType.INITIAL_REWARD,
    #     id_model="2026-05-18 22:25:23",   # replace with your model timestamp
    # )