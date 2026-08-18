"""The training runner: turns an `RLMode` into a completed RL run.

`RLRunner` is the RL sibling of `app.runners.ScenarioRunner` -- same
constructor shape, same `run()` -- and it dispatches on `RLMode`: train a fresh
model, search hyperparameters, do both, load a saved model and watch it, or
replay a recorded episode. It is the only module that needs to know how
algorithms, observations, rewards, the environment factory and disk I/O fit
together.
"""
