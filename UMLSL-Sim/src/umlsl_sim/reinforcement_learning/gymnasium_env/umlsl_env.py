import random
import time

import numpy as np

from abc import ABC, abstractmethod
from gymnasium import Env
from gymnasium import spaces
from typing import TYPE_CHECKING, Tuple, Dict
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.constants import MAX_ACC, MAX_DEC, TIME_PER_FRAME
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.abstract_observation import Observation
from umlsl_sim.reinforcement_learning.rl_constants import MAX_EPISODE_STEPS

# pyglet and GameWindow are imported lazily so headless training and unit
# tests can import this module without pulling in the GUI stack.
if TYPE_CHECKING:
    from umlsl_sim.car_control.action_shield import ActionShield

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
    - Lane change: [0, 1, 2] → maps to [-1, 0, 1]
    
    ## Episode Termination

    Episodes end when:
    - `done=True`: Agent reached goal or collision (terminal state)
    - `truncated=True`: Deadlock detected (time limit equivalent)

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
        game_window (GameWindow | None): Pygame window for rendering
        action_space (spaces.MultiDiscrete): Agent action space specification
        observation_space (spaces.Space): Agent observation space specification
        render_mode (str | None): Rendering mode ('human' or None)
        action_shield (ActionShield | None): Safety shield, or None when the
            agent's action set is unrestricted
    """

    def __init__(self, 
                 game_model: TrafficEnv,
                 observation_model: Observation,
                 render_mode: None | RenderMode = None,
                 show_reservation: bool = True,
                 ):
        """Initialize the Gymnasium environment.
        
        Args:
            game_model (TrafficEnv): The traffic simulation to control.
            observation_model (Observation): Model for generating observations from game state.
            render_mode (None | str): Rendering mode. 'human' for visual display, None for headless.
        """
        
        self.render_mode = render_mode
        self.show_reservation = show_reservation

        self.game_model: TrafficEnv = game_model

        if self.render_mode == RenderMode.GUI:
            from umlsl_sim.gui.simulation_window import GameWindow

            self.game_window = GameWindow(
                self.game_model.cars,
                self.game_model.roads,
                self.game_model.reservation_management,
                self.show_reservation
                )
        else:
            self.game_window = None

        self.agent_score: int = self.game_model.agent_car.score

        self.observation_model: Observation = observation_model

        # accelaration = [0, MAX_DEC + MAX_ACC] and lange changes = [0, 2]
        self.action_space = spaces.MultiDiscrete([MAX_ACC + MAX_DEC + 1, 3])
        self.observation_space = self.observation_model.space()

        # Off by default: an unshielded env allows every action, which is what
        # the reward-based safety profiles expect.
        self.action_shield: "ActionShield | None" = None

        self.done: bool = False
        self.truncated: bool = False
        self.episode_step: int = 0

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
                - actions[1]: Lane change command [0, 1, 2]
        
        Returns:
            Tuple[observation, reward, done, truncated, info]:
                - observation: New observation from observation model
                - reward: Scalar reward from compute_reward()
                - done (bool): True if episode is terminal (goal/collision)
                - truncated (bool): True if episode ended by deadlock
                - info (dict): Debugging information
        """
        # accelaration = [-MAX_DEC, MAX_ACC] and lange changes = [-1, 0, 1]
        decoded_action = (actions[0] - MAX_DEC, actions[1] - 1)

        self.last_decoded_action: Tuple[int, int] = decoded_action
        self._pre_step(decoded_action)

        self.result = self.game_model.play_step(action=decoded_action)
        self.episode_step += 1

        observation = self.observation_model.observe()

        reward = self.compute_reward()

        self.done = False
        self.truncated = False

        if self.result == "game_over":
            self.done = True
        elif self.result == "deadlock":
            self.truncated = True
        elif self.game_model.agent_car is not None and self.game_model.agent_car.get_death_status():
            # Agent crashed; the RL episode is functionally over even if NPCs
            # keep running. Without this, evaluate_policy can hang forever.
            self.done = True
        elif self.episode_step >= MAX_EPISODE_STEPS:
            self.truncated = True

        info = self._get_info() # for debugging

        if self.done or self.truncated:
            self.map_history = self.game_model.game_history.map.copy()
            self.car_history = self.game_model.game_history.list_of_cars.copy()
            self.action_history = self.game_model.game_history.action_history_dict.copy()
            self.action_length_history = self.game_model.game_history.action_length

        return observation, reward, self.done, self.truncated, info
    
    def render(self):
        """Render the current game state visually.
        
        If render_mode is RenderMode.GUI, displays the traffic simulation on screen
        with appropriate frame rate control. Does nothing if render_mode is None.
        """
        if self.game_window:
            self._render_frame()
            time.sleep(1.0 / TIME_PER_FRAME)

    def _render_frame(self):
        """Render a single frame to the display window.

        Handles display events, drawing, and frame refresh using Pyglet.
        """
        import pyglet

        self.game_window.dispatch_events()
        self.game_window.on_draw()
        pyglet.clock.tick()
        self.game_window.flip()

    def enable_action_shield(self) -> "ActionShield":
        """Attach a safety shield, switching this env to masked actions.

        Called by the controller when the selected algorithm consumes action
        masks (see `RLAlgorithm.requires_action_masks`). Idempotent: a second
        call returns the shield already in place, keeping its counters.

        Returns:
            ActionShield: The shield now serving `action_masks()`.
        """
        if self.action_shield is None:
            from umlsl_sim.car_control.action_shield import ActionShield

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
                flags followed by 3 lane-change flags. All true when no shield
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