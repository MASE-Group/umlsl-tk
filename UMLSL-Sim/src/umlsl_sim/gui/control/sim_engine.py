"""Frame-by-frame driver for both plain and RL simulations.

The control window owns the pyglet event loop, so this engine does **not** call
``pyglet.app.run()`` or open its own window (unlike the standalone
``GameController``). Instead it exposes :meth:`step` to advance the simulation
one action and :meth:`world` to hand the current roads / cars / reservations to
the scene renderer.

Two run modes are supported:

* ``plain``   – NPC-only ``TrafficEnv.play_step()`` loop.
* ``rl_eval`` – load a saved model and drive ``env.step(model.predict(obs))``.
  Models trained behind the safety shield are run behind it too, with the
  current action mask handed to every prediction.

RL training / optimization is long-running and headless; it lives in
``rl_support`` and runs on a worker thread rather than here.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from umlsl_sim.constants import FLASH_CYCLE, TIME_PER_FRAME
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.scenario_io.car_spec import CarSpec

log = logging.getLogger(__name__)

# How many simulation steps to advance per second while playing.
STEPS_PER_SECOND = 30
STEP_INTERVAL = 1.0 / STEPS_PER_SECOND


class SimulationEngine:
    def __init__(self) -> None:
        self.mode: Optional[str] = None            # None | "plain" | "rl_eval"
        self.paused: bool = True
        self.finished: bool = False
        self.status: str = "No simulation loaded."
        self.flash_count: int = 0

        self.game_model: Optional[TrafficEnv] = None
        self._env = None
        self._model = None
        self._obs = None
        # Set for shielded models: returns the current action mask to hand to
        # predict(). None for ordinary models.
        self._action_masks: Optional[Callable[[], object]] = None
        self._restart: Optional[Callable[[], None]] = None
        self._on_finish: Optional[Callable[[str], None]] = None

    # --- lifecycle --------------------------------------------------------
    @property
    def active(self) -> bool:
        return self.mode is not None

    @property
    def can_restart(self) -> bool:
        return self._restart is not None

    @property
    def agent_car_name(self) -> Optional[str]:
        """Name of the car the RL agent drives, or ``None`` outside RL eval.

        Cars are named after their colour ("White", "Maroon", ...), so this
        doubles as the label the GUI shows to point the user at the agent.
        """
        if self.mode != "rl_eval" or self.game_model is None:
            return None
        car = self.game_model.agent_car
        return car.name or None if car is not None else None

    def set_finish_callback(self, cb: Callable[[str], None]) -> None:
        self._on_finish = cb

    def start_plain(
        self,
        roads,
        players: int,
        predefined_cars: Optional[List[CarSpec]],
        show_reservation: bool,
    ) -> None:
        def _build() -> None:
            self.game_model = TrafficEnv(
                roads=roads, players=players, predefined_cars=predefined_cars
            )
            self.game_model.reset()
            self._env = None
            self._model = None
            self._obs = None
            self.mode = "plain"
            self.paused = False
            self.finished = False
            self.flash_count = 0
            self.status = "Running."

        self._restart = _build
        _build()

    def start_rl_eval(
        self,
        roads,
        players: int,
        predefined_cars: Optional[List[CarSpec]],
        show_reservation: bool,
        scenario_name: str,
        rl_algorithm_type,
        observation_model_type,
        reward_type,
        id_model: str,
    ) -> None:
        # Imported lazily; RL extras may not be installed.
        from umlsl_sim.reinforcement_learning.rl_modes import RLMode
        from umlsl_sim.reinforcement_learning.gymnasium_env.reward_registry import get_reward_model
        from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_registry import (
            get_observation_model,
        )
        from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_registry import get_rl_algo
        from umlsl_sim.reinforcement_learning.rl_io import get_path_center, load_best_model

        def _build() -> None:
            game_model = TrafficEnv(
                roads=roads,
                players=players,
                predefined_cars=predefined_cars,
                rl_mode=RLMode.LOAD_TRAINED_MODEL,
            )
            observation_model = get_observation_model(observation_model_type)(game_model)
            env_class = get_reward_model(reward_type)
            env = env_class(
                game_model=game_model,
                observation_model=observation_model,
                render_mode=RenderMode.NO_GUI,   # we render ourselves
                show_reservation=show_reservation,
            )
            # A model trained behind the safety shield must be run behind it
            # too: the mask is part of the policy, not of the training loop.
            algo_class = get_rl_algo(rl_algorithm_type)
            if algo_class.requires_action_masks:
                env.enable_action_shield()

            rl_algorithm = algo_class(env)
            path_center = get_path_center(
                scenario=scenario_name,
                rl_algo=rl_algorithm_type.name,
                obs_model=observation_model_type.name,
                reward_type=reward_type.name,
            )
            model = load_best_model(path_center, id_model, rl_algorithm, env)

            self.game_model = game_model
            self._env = env
            self._model = model
            self._action_masks = env.action_masks if algo_class.requires_action_masks else None
            self._obs, _info = env.reset()
            self.mode = "rl_eval"
            self.paused = False
            self.finished = False
            self.flash_count = 0
            self.status = "Running trained model."

        self._restart = _build
        _build()

    def rerun(self) -> None:
        if self._restart is not None:
            self._restart()

    def clear(self) -> None:
        self.mode = None
        self.paused = True
        self.finished = False
        self.game_model = None
        self._env = None
        self._model = None
        self._obs = None
        self._action_masks = None
        self._restart = None
        self.status = "No simulation loaded."

    # --- per-frame update -------------------------------------------------
    def toggle_pause(self) -> None:
        if not self.active or self.finished:
            return
        self.paused = not self.paused
        self.status = "Paused." if self.paused else "Running."

    def update(self, _dt: float) -> None:
        # advance the dead-car flash animation regardless of pause state
        self.flash_count += TIME_PER_FRAME if self.flash_count < FLASH_CYCLE else -self.flash_count
        if not self.active or self.paused or self.finished:
            return
        try:
            self._step_once()
        except Exception as exc:  # keep the GUI alive on model errors
            log.exception("Simulation step failed")
            self._finish(f"Error: {exc}")

    def _step_once(self) -> None:
        if self.mode == "plain":
            result = self.game_model.play_step()
            if result is not None:
                self._finish("Game over." if result == "game_over" else "Deadlock.")
        elif self.mode == "rl_eval":
            if self._action_masks is None:
                action, _ = self._model.predict(self._obs, deterministic=True)
            else:
                action, _ = self._model.predict(
                    self._obs, deterministic=True, action_masks=self._action_masks()
                )
            self._obs, _reward, terminated, truncated, _info = self._env.step(action)
            if terminated or truncated:
                self._finish("Episode finished." if terminated else "Episode truncated.")

    def _finish(self, message: str) -> None:
        self.finished = True
        self.paused = True
        self.status = message
        if self._on_finish:
            self._on_finish(message)

    # --- rendering data ---------------------------------------------------
    def world(self):
        """(roads, cars, reservation_management) for the scene renderer, or None."""
        if self.game_model is None:
            return None
        gm = self.game_model
        return gm.roads, gm.cars, gm.reservation_management
