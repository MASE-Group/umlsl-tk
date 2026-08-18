"""Runners: the loop that drives a world from its start to the end of a run.

A runner owns the loop, decides when a run is over, and hands frames to a
`Renderer`. `SimulationRunner` is the shape they share -- roads, a car count, a
render mode, a renderer, and a `run()`; `ScenarioRunner` is the NPC-traffic
implementation of it.

The RL implementation lives with the rest of the RL stack, in
`umlsl_sim.rl.training.rl_runner`, and inherits the same base from here. That is
why this package sits beside `app` rather than inside it: both a plain run and a
training run are runners, and neither should have to reach up into the
entry-point layer to say so. `umlsl_sim.app.main` picks between them.
"""

from umlsl_sim.runners.runner import SimulationRunner
from umlsl_sim.runners.scenario_runner import ScenarioRunner

__all__ = ["SimulationRunner", "ScenarioRunner"]
