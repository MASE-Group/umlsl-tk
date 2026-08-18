import random

import numpy as np

from abc import ABC, abstractmethod
from dataclasses import dataclass
from gymnasium import Env
from gymnasium import spaces
from typing import TYPE_CHECKING, List, Tuple, Dict
from umlsl_sim.simulation.ports import Renderer, create_renderer
from umlsl_sim.simulation.traffic_environment import CarState, TrafficEnv
from umlsl_sim.config.logic_constants import MAX_ACC, MAX_DEC
from umlsl_sim.config.simulation_constants import DEADLOCK_FRAMES
from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.rl.observations.observation_model import Observation
from umlsl_sim.rl.constants import MAX_EPISODE_STEPS

# No GUI import anywhere in this module: rendering goes through the Renderer
# port, so a headless install without pyglet can still import and train here.
if TYPE_CHECKING:
    from umlsl_sim.control.safety.action_shield import ActionShield


@dataclass(frozen=True)
class EpisodeEnd:
    """How an episode finished, captured before anything could reset it.

    Evaluation runs the environment inside SB3's `DummyVecEnv`, which resets as
    soon as an episode ends, and `TrafficEnv.reset()` replaces every car. Code
    that reports on the run afterwards -- `RLRunner.run()` -- would
    therefore describe the fresh world the reset built, with every score back
    at 0 and every car alive, rather than the episode that was just watched.
    This is that episode, as plain data.

    Attributes:
        steps (int): How many steps the episode lasted.
        reason (str): Why it ended, in words, for reporting.
        car_states (List[CarState]): Every car's score and death status on the
            final step.
    """

    steps: int
    reason: str
    car_states: List[CarState]


class MlslEnv(Env, ABC):
    """Abstract Gymnasium environment for MLSL traffic simulation.
    
    This class provides the bridge between the traffic simulation and reinforcement learning
    algorithms by implementing the Gymnasium API. It manages the simulation loop where the
    agent takes actions and receives observations and rewards.
    
    ## Core Gymnasium Loop
    
    The interaction follows the standard RL loop:
    ```
    obs, info = env.reset()
    while not done:
        obs, reward, terminated, truncated, info = env.step(action)
        env.render()  # optional
    ```
    
    ## How to Create a Concrete Environment
    
    Subclass MlslEnv with a specific reward function:
    
    ```python
    @register_reward_model(RewardType.MY_REWARD)
    class MyRewardEnv(MlslEnv):
        def compute_reward(self) -> float:
            # Return numeric reward based on game state
            if collision:
                return -10.0
            elif reached_goal:
                return 100.0
            else:
                return -0.01
    ```
    
    The decorator automatically registers it with the reward_registry for easy lookup.
    
    ## Action Space
    
    MultiDiscrete with 2 components:
    - Acceleration: [0, MAX_ACC + MAX_DEC] → maps to [-MAX_DEC, MAX_ACC]
    - Lane command: [0, 1, 2, 3] → maps to [-1, 0, 1, 2], i.e. change right,
      stay, change left, withdraw a pending claim. A lane change starts as a
      claim on the target lane that the agent may take back for the next
      CLAIM_TIME steps; withdrawing is what takes it back (see
      `Car.change_lane`). Withdrawing with no claim pending is simply a step
      in which nothing happens.
    
    ## Episode Termination

    Episodes end when:
    - `done=True`: every car is out of play, or the agent car crashed
    - `truncated=True`: deadlock detected, or `max_episode_steps` reached

    Whichever it was is recorded in `episode_end`, together with the final
    scores, so a run can be reported on after the environment has been reset.

    ## Safety Shield (optional)

    Safety can be enforced by masking instead of by reward shaping. Call
    `enable_action_shield()` to attach an `ActionShield`; `action_masks()` then
    reports which actions the SafetyController considers safe, and a masking
    algorithm (`RLAlgorithmType.MASKABLE_PPO`) never samples the others. Without
    it, `action_masks()` allows everything and behaviour is unchanged, so
    reward-based safety keeps working exactly as before.

    ## Attributes
        game_model (TrafficEnv): The traffic simulation instance
        observation_model (Observation): Converts game state to observations
        renderer (Renderer): Where frames go; a NullRenderer when headless
        action_space (spaces.MultiDiscrete): Agent action space specification
        observation_space (spaces.Space): Agent observation space specification
        render_mode (str | None): Rendering mode ('human' or None)
        action_shield (ActionShield | None): Safety shield, or None when the
            agent's action set is unrestricted
        max_episode_steps (int): Step cap after which an episode is truncated
        episode_end (EpisodeEnd | None): How the last completed episode ended,
            or None before the first one finishes
    """

    def __init__(self,
                 game_model: TrafficEnv,
                 observation_model: Observation,
                 render_mode: None | RenderMode = None,
                 show_reservation: bool = True,
                 max_episode_steps: int = MAX_EPISODE_STEPS,
                 ):
        """Initialize the Gymnasium environment.

        Args:
            game_model (TrafficEnv): The traffic simulation to control.
            observation_model (Observation): Model for generating observations from game state.
            render_mode (None | str): Rendering mode. 'human' for visual display, None for headless.
            max_episode_steps (int): Steps after which an episode is truncated.
                Defaults to the training cap; a run that is watched rather than
                learned from can afford a longer one (see DEMO_EPISODE_STEPS).
        """

        self.render_mode = render_mode
        self.show_reservation = show_reservation
        self.max_episode_steps = max_episode_steps

        self.game_model: TrafficEnv = game_model

        # Presentation goes through the port: a GUI run gets whatever renderer
        # the composition root registered, a headless one gets a NullRenderer.
        # Either way this module has no idea what is drawing it.
        self.renderer: Renderer = create_renderer(
            self.render_mode if self.render_mode is not None else RenderMode.NO_GUI,
            self.show_reservation,
        )
        if self.render_mode == RenderMode.GUI:
            self.renderer.bind(
                self.game_model.cars,
                self.game_model.roads,
                self.game_model.reservation_management,
            )

        self.agent_score: int = self.game_model.agent_car.score

        self.observation_model: Observation = observation_model

        # accelaration = [0, MAX_DEC + MAX_ACC] and lane commands = [0, 3]
        self.action_space = spaces.MultiDiscrete([MAX_ACC + MAX_DEC + 1, 4])
        self.observation_space = self.observation_model.space()

        # Off by default: an unshielded env allows every action, which is what
        # the reward-based safety profiles expect.
        self.action_shield: "ActionShield | None" = None

        self.done: bool = False
        self.truncated: bool = False
        self.episode_step: int = 0

        # Deliberately not cleared by reset(): outliving the reset is the whole
        # point of it (see EpisodeEnd).
        self.episode_end: None | EpisodeEnd = None

        self.map_history = self.game_model.game_history.map.copy()
        self.car_history = self.game_model.game_history.list_of_cars.copy()
        self.action_history = self.game_model.game_history.action_history_dict.copy()
        self.action_length_history = self.game_model.game_history.action_length

    def reset(self, seed: None | int = None, options: None | Dict = None) -> Tuple[spaces.Space, Dict[str, any]]:
        """Reset the environment to initial state.
        
        Resets the traffic simulation to its starting condition and returns the
        initial observation. This must be called before each episode.
        
        Args:
            seed (None | int): Random seed for reproducibility. Seeds both
                Gymnasium's `self.np_random` and the `random` module, which is
                what TrafficEnv draws car placements, sizes and speeds from.
            options (None | Dict): Additional options (currently unused).

        Returns:
            Tuple[spaces.Space, Dict]:
                - observation: Initial observation from the observation model
                - info: Dictionary with auxiliary information for debugging
        """
        super().reset(seed=seed)
        if seed is not None:
            random.seed(seed)
        self.game_model.reset()
        # The agent car is rebuilt by the reset above, so its score restarts at
        # 0; carrying the previous episode's high-water mark over would suppress
        # goal rewards until the agent beat it again.
        self.agent_score = self.game_model.agent_car.score
        self.episode_step = 0
        self.done = False
        self.truncated = False
        return (self.observation_model.observe(), self._get_info())
    
    def step(self, actions: Tuple[int, int]) -> Tuple[spaces.Space, float, bool, bool, Dict[str, any]]:
        """Execute one environment step.
        
        Processes the agent's action, updates the simulation, and returns the
        new observation, reward, and episode status.
        
        Args:
            actions (Tuple[int, int]): Two-element action vector:
                - actions[0]: Acceleration command [0, MAX_ACC + MAX_DEC]
                - actions[1]: Lane command [0, 1, 2, 3]
        
        Returns:
            Tuple[observation, reward, done, truncated, info]:
                - observation: New observation from observation model
                - reward: Scalar reward from compute_reward()
                - done (bool): True if episode is terminal (goal/collision)
                - truncated (bool): True if episode ended by deadlock
                - info (dict): Debugging information
        """
        # accelaration = [-MAX_DEC, MAX_ACC] and lane commands = [-1, 0, 1, 2]
        decoded_action = (actions[0] - MAX_DEC, actions[1] - 1)

        self.last_decoded_action: Tuple[int, int] = decoded_action
        self._pre_step(decoded_action)

        self.result = self.game_model.play_step(action=decoded_action)
        self.episode_step += 1

        observation = self.observation_model.observe()

        reward = self.compute_reward()

        self.done = False
        self.truncated = False
        # Recorded alongside the flags so every way an episode can end names
        # itself. Only the game_over and deadlock cases announce themselves in
        # the simulation log; the step cap in particular used to end a run in
        # silence, leaving nothing to explain why the window had closed.
        end_reason: None | str = None

        if self.result == "game_over":
            self.done = True
            end_reason = "every car is out of play"
        elif self.result == "deadlock":
            self.truncated = True
            end_reason = f"gridlock (no living car moved for {DEADLOCK_FRAMES} frames)"
        elif self.game_model.agent_car is not None and self.game_model.agent_car.get_death_status():
            # Agent crashed; the RL episode is functionally over even if NPCs
            # keep running. Without this, evaluate_policy can hang forever.
            self.done = True
            end_reason = "the agent car crashed"
        elif self.episode_step >= self.max_episode_steps:
            self.truncated = True
            end_reason = f"step limit reached ({self.max_episode_steps} steps)"

        info = self._get_info() # for debugging

        if self.done or self.truncated:
            self.map_history = self.game_model.game_history.map.copy()
            self.car_history = self.game_model.game_history.list_of_cars.copy()
            self.action_history = self.game_model.game_history.action_history_dict.copy()
            self.action_length_history = self.game_model.game_history.action_length
            self.episode_end = EpisodeEnd(
                self.episode_step, end_reason, self.game_model.car_states()
            )

        return observation, reward, self.done, self.truncated, info
    
    def render(self):
        """Draw the current state through the renderer.

        A headless run's renderer draws nothing, so this is a no-op there rather
        than a special case that has to be guarded at every call site. Frame
        pacing belongs to the renderer, not here.
        """
        self.renderer.draw_frame()

    def close(self) -> None:
        """Close the render window, if this environment opened one.

        Gymnasium's default `close()` is a no-op, which left the pyglet window
        alive until interpreter shutdown. On macOS that is too late: the window
        is torn down after its Cocoa delegate has been released, so the
        resign-key notification fires against a delegate whose `_window` is
        gone and prints an "Exception ignored ... has no attribute _window"
        traceback. Closing here happens while the delegate is still attached,
        so the notification is handled normally.
        """
        self.renderer.close()

    def enable_action_shield(self) -> "ActionShield":
        """Attach a safety shield, switching this env to masked actions.

        Called by the controller when the selected algorithm consumes action
        masks (see `RLAlgorithm.requires_action_masks`). Idempotent: a second
        call returns the shield already in place, keeping its counters.

        Returns:
            ActionShield: The shield now serving `action_masks()`.
        """
        if self.action_shield is None:
            from umlsl_sim.control.safety.action_shield import ActionShield

            self.action_shield = ActionShield(self.game_model)
        return self.action_shield

    def action_masks(self) -> np.ndarray:
        """Report which actions are currently available to the agent.

        This is the hook sb3-contrib's maskable algorithms look for (through
        `get_wrapper_attr`, so wrapping in Monitor keeps it reachable). It is
        queried before each action is chosen, i.e. against the pre-step state.

        Returns:
            np.ndarray: Boolean array with one entry per value of each action
                dimension, concatenated: `MAX_ACC + MAX_DEC + 1` acceleration
                flags followed by 4 lane-command flags. All true when no shield
                is attached.
        """
        if self.action_shield is None:
            return np.ones(int(self.action_space.nvec.sum()), dtype=bool)
        return self.action_shield.action_masks()

    def _pre_step(self, decoded_action: Tuple[int, int]) -> None:
        """Hook invoked just before the simulation advances on each step.

        Subclasses override this to inspect the pre-step game state — for
        example, to query a SafetyController for the action the agent is
        about to take. Default implementation is a no-op.
        """
        pass

    @abstractmethod
    def compute_reward(self) -> float:
        """Compute the reward signal for the current step.
        
        This is implemented by subclasses to define the reward strategy.
        The reward signal guides learning by evaluating the quality of actions.
        
        Returns:
            float: Scalar reward value. Convention:
                - Positive for desirable outcomes (reaching goal, efficient progress)
                - Negative for undesirable outcomes (collisions, inefficient behavior)
                - Small magnitude for step-wise costs/bonuses
        
        Example:
            ```python
            def compute_reward(self) -> float:
                if self.game_model.collision_detected:
                    return -100.0
                elif self.game_model.agent_reached_goal:
                    return 1000.0
                else:
                    return -0.1  # small step cost
            ```
        """
        ...
    
    def _get_info(self) -> Dict:
        """Get auxiliary information for debugging.

        Returns:
            Dict: Debugging information (empty dict in base implementation).
        """
        return {}