"""The Gymnasium adapter: `TrafficEnv` presented as a standard RL environment.

`MlslEnv` is the base; a reward profile from `rl.rewards` subclasses it to
supply `compute_reward`, so the class an algorithm actually trains against is
built by `EnvSpec.build()`, not named here.
"""
