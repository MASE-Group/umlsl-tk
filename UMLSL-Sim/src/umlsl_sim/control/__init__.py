"""The car controllers: given a car and its surroundings, what should it do?

Two independent implementations live here, and they are used for different
purposes:

* `control.astar` -- the **NPC controller**. It plans a route with A* and picks
  the acceleration and lane change that follow it safely. This is what drives
  every non-agent car, and it satisfies `simulation.ports.CarController`, so
  `TrafficEnv(npc_controller_factory=...)` swaps it out wholesale.
* `control.safety` -- the **safety controller** and the action shield built on
  it. It answers "which actions are safe *right now*" rather than "which action
  is best", and that answer feeds RL training in two ways: as a mask, so a
  masking algorithm never samples an unsafe action (`ActionShield`), or as a
  penalty term in a reward profile (`rl.rewards.safety_aware_reward`).

Both read the simulation state and neither writes it: a controller returns an
action, and only `TrafficEnv` applies one.
"""

from umlsl_sim.control.astar.astar_car_controller import AstarCarController
from umlsl_sim.control.safety.safety_controller import SafetyController

__all__ = ["AstarCarController", "SafetyController"]
