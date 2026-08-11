# Deferred annotations: main()'s signature names the RL types, which are only
# importable when the optional [rl] extra is installed. Without this, defining
# main() raises NameError on a non-RL install (Python < 3.14).
from __future__ import annotations

import logging
from typing import List

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(filename)s:%(lineno)s | %(message)s')

from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.scenario_io.car_spec import CarSpec
from umlsl_sim.simulation.controllers.abstract_simulation_controller import AbstractGameController
from umlsl_sim.simulation.controllers.simulation_controller import GameController
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
RL_IMPORT_ERROR: None | ImportError = None
try:
    from umlsl_sim.simulation.controllers.rl_simulation_controller import RLGameController
    from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
    from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import ObservationModelType
    from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType
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
        controller: AbstractGameController = GameController(
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
        controller: AbstractGameController = RLGameController(
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

    controller.run()

if __name__ == '__main__':

    scenario = load_scenario("TWO_CROSSINGS")

    # Plain simulation: NPC cars driven by the A* controller, no RL involved.
    # This is the default because it needs no trained model and no [rl] extra.
    main(**scenario, render_mode=RenderMode.GUI, show_reservation=True)

    # --- Reinforcement-learning variants ------------------------------------
    # Uncomment one of these instead. They need the [rl] extra installed, and
    # the LOAD_* modes need an `id_*` that actually exists under rl_results/ —
    # see UMLSL-Sim/README.md, "Finding Model/History IDs".

    # Train an agent from scratch:
    # main(
    #     **scenario,
    #     render_mode=RenderMode.NO_GUI,
    #     show_reservation=False,
    #     rl_mode=RLMode.TRAIN,
    #     rl_algorithm_type=RLAlgorithmType.PPO,
    #     observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    #     reward_type=RewardType.INITIAL_REWARD,
    # )

    # Watch a previously trained agent:
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