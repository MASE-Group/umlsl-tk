"""Reward profiles: what the agent is scored on.

Each profile is a subclass of `MlslEnv` that implements `compute_reward`, tagged
with `@register_reward_model(RewardType.X)`; `get_reward_model(RewardType.X)`
returns it. Adding a profile is a new module here plus an enum member -- no
consumer changes, because the runner only ever names a `RewardType`.

The two shipped profiles pair with the two safety mechanisms:

* `initial_reward` -- scores the objective alone (goals, crashes, deadlock).
  Use it when the safety shield is masking unsafe actions away.
* `safety_aware_reward` -- additionally penalises unsafe accelerations and lane
  changes, as judged by `control.safety.SafetyController`. Use it when the agent
  is free to choose unsafe actions and must learn not to.

The registry is populated on first lookup, not on import: `get_*` calls this
package's `load_plugins()`, which imports every module in it so the decorators
run. Keeping it off the import path means naming a type costs nothing.
"""

from umlsl_sim.rl.plugin_loader import package_loader

#: Imports every module in this package so the decorators run and the registry
#: is populated. Called by the registry lookup, not on import -- see
#: `rl.plugin_loader`.
load_plugins = package_loader(__name__, __file__)
