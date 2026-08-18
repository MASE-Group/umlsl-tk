"""UMLSL-Sim: a discrete-time traffic simulator and Gymnasium environment.

The package is a stack. Each layer depends only on the ones below it, and each
is replaceable on its own because the layer above names an interface rather than
an implementation:

    app/           entry points -- the composition root that wires it all up
    ├── runners/   the loop that drives a run to its end
    ├── gui/       pyglet windows, drawing, control panel  (Renderer port)
    ├── rl/        algorithms, hyperparameters, observations, rewards
    ├── control/   car controllers: A* for NPCs, safety for RL (CarController port)
    ├── scenario/  the scenario parser: JSON in, a world description out
    ├── factories/ model creators: cars, goals, segments, and the CarSpec they read
    ├── simulation/the traffic logic, and the ports it is driven through
    ├── palettes/  named colour tables (plain data)
    └── config/    the model's constants and the render mode (plain data)

The two seams worth knowing about, both declared in `simulation.ports`:

* `CarController` -- what drives an NPC. `TrafficEnv(npc_controller_factory=...)`
  takes any callable matching it; `umlsl_sim.control` supplies the default.
* `Renderer` -- where frames go. `umlsl_sim.app` registers the pyglet
  implementation on import; a headless run gets a `NullRenderer` and never
  imports a GUI toolkit.

Start reading at `simulation/traffic_environment.py` for the logic, or at
`app/main.py` for how a run is assembled.
"""
