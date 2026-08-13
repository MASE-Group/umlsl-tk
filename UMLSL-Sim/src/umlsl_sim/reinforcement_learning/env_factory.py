"""Recipe for building the environments an RL run needs.

An `EnvSpec` is the *description* of a training environment -- road network,
car count, observation model, reward profile, whether a safety shield is
attached -- kept separate from any environment built from it. That separation
buys three things:

* **Evaluation gets its own world.** `EvalCallback` must not be handed the
  environment being trained on: evaluating resets it, which discards the
  half-collected rollout the agent was in the middle of and lets evaluation
  episodes bleed into training ones. Building a second environment from the
  same spec costs one construction (~1 s) and removes the interference.
* **Hyperparameter trials stay independent.** Each Optuna trial builds its own
  environment, so a trial cannot inherit the simulation state -- car positions,
  reservations, intersection priorities -- left behind by the previous one.
* **The search can run in separate processes.** An `EnvSpec` is picklable
  (a road network is plain data); a live environment, with its Gymnasium
  wrappers and torch tensors, is not worth shipping across a process boundary.

Every `build()` deep-copies the road network, because `TrafficEnv` mutates it:
segment reservations, intersection priorities and crossing state all live on the
`Road` objects. Two environments sharing one network would silently corrupt each
other's traffic.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, List, Tuple

from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import ObservationModelType
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType
from umlsl_sim.scenario_io.car_spec import CarSpec
from umlsl_sim.simulation.road_network.road_network import Road

if TYPE_CHECKING:
    from stable_baselines3.common.monitor import Monitor

    from umlsl_sim.car_control.action_shield import ActionShield


@dataclass(frozen=True)
class EnvSpec:
    """Everything needed to build one MLSL training environment.

    Attributes:
        roads (List[Road]): The road network. Deep-copied on every build, so the
            caller's network is never mutated by training.
        players (int): Number of NPC cars; the RL agent is spawned on top.
        predefined_cars (List[CarSpec]): Scenario-supplied car specs, if any.
        observation_model_type (ObservationModelType): How game state becomes an
            observation vector.
        reward_type (RewardType): Which reward profile the environment scores by.
        uses_action_masks (bool): Whether to attach the safety shield. Read from
            the algorithm's `requires_action_masks`; masking algorithms need it,
            and an evaluation environment needs it too or the policy would be
            scored without the shield it trained under.
        rl_mode (RLMode): Passed to `TrafficEnv` so it spawns an agent car.
        render_mode (RenderMode): GUI environments open a window, so anything
            built for background evaluation or a worker process must stay
            headless.
        show_reservation (bool): GUI-only; draws segment reservations.
    """

    roads: List[Road]
    players: int
    observation_model_type: ObservationModelType
    reward_type: RewardType
    uses_action_masks: bool
    predefined_cars: List[CarSpec] = field(default_factory=list)
    rl_mode: RLMode = RLMode.TRAIN
    render_mode: RenderMode = RenderMode.NO_GUI
    show_reservation: bool = False

    def build(self) -> Tuple["Monitor", "ActionShield | None"]:
        """Build one environment from this spec.

        Returns:
            Tuple[Monitor, ActionShield | None]: The Monitor-wrapped
                environment (Monitor records episode reward and length, and
                keeps `action_masks` reachable through `get_wrapper_attr`), and
                the safety shield attached to it, or None when this spec does
                not use masking.
        """
        from stable_baselines3.common.monitor import Monitor

        from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_registry import get_observation_model
        from umlsl_sim.reinforcement_learning.gymnasium_env.reward_registry import get_reward_model
        from umlsl_sim.simulation.traffic_environment import TrafficEnv

        game_model = TrafficEnv(
            roads=copy.deepcopy(self.roads),
            players=self.players,
            predefined_cars=copy.deepcopy(self.predefined_cars),
            rl_mode=self.rl_mode,
        )

        observation_model = get_observation_model(self.observation_model_type)(game_model)

        env = get_reward_model(self.reward_type)(
            game_model=game_model,
            observation_model=observation_model,
            render_mode=self.render_mode,
            show_reservation=self.show_reservation,
        )

        # Before any wrapper: the shield belongs to the environment itself.
        shield = env.enable_action_shield() if self.uses_action_masks else None

        return Monitor(env), shield

    def headless(self) -> "EnvSpec":
        """A copy of this spec that never opens a window.

        Used for evaluation environments and for worker processes: a second GUI
        window would compete with the one the run already owns, and rendering an
        evaluation the user is not watching is pure cost.
        """
        if self.render_mode is RenderMode.NO_GUI:
            return self
        return replace(self, render_mode=RenderMode.NO_GUI, show_reservation=False)
