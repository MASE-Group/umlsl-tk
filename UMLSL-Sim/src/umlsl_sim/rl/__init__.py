"""Reinforcement learning: training an agent to drive in the simulation.

The RL stack depends on the simulation but never the other way round -- nothing
in `umlsl_sim.simulation` knows this package exists. It is assembled from four
independently replaceable parts, each behind a registry so that adding an
alternative is a new module plus a decorator, never an edit to a consumer:

* `algorithms` -- the training algorithm (`RLAlgorithmType` -> `RLAlgorithm`).
  PPO leaves safety to the reward; MaskablePPO consumes the safety shield's
  action masks.
* `hyperparameters` -- the Optuna search that tunes an algorithm's parameters.
* `observations` -- what the agent sees (`ObservationModelType` -> `Observation`):
  simulation state in, a Gymnasium space and a vector out.
* `rewards` -- what the agent is scored on (`RewardType` -> a reward profile).

Around them: `gym_env` (the Gymnasium `Env` wrapping `TrafficEnv`), `env_factory`
(a picklable recipe for building one), `rl_io` (models, histories and studies on
disk), and `training` (the runner that ties a mode to those pieces).

Optional dependency: this package needs the `[rl]` extra. Everything else in
umlsl_sim imports and runs without it.
"""
