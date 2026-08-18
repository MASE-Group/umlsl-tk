"""Training algorithms: how a policy is learned from the environment.

Each algorithm subclasses `RLAlgorithm` and is tagged with
`@register_rl_algorithm(RLAlgorithmType.X)`; `get_rl_algo(RLAlgorithmType.X)`
returns it. The runner names a type and never a class, so an alternative learner
is a new module here plus an enum member.

The two shipped algorithms differ in how they treat safety:

* `ppo_algorithm` -- plain PPO. Every action is available, so unsafe ones have
  to be discouraged by the reward (`RewardType.SAFETY_AWARE_REWARD`).
* `maskable_ppo_algorithm` -- MaskablePPO. It declares `requires_action_masks`,
  which makes the environment attach the safety shield and hide unsafe actions
  before sampling, freeing the reward to score the objective alone.

The registry is populated on first lookup, not on import: `get_*` calls this
package's `load_plugins()`, which imports every module in it so the decorators
run. Keeping it off the import path means naming a type costs nothing.
"""

from umlsl_sim.rl.plugin_loader import package_loader

#: Imports every module in this package so the decorators run and the registry
#: is populated. Called by the registry lookup, not on import -- see
#: `rl.plugin_loader`.
load_plugins = package_loader(__name__, __file__)
