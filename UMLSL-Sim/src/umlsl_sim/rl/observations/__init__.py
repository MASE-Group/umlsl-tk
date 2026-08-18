"""Observation models: what the agent sees each step.

Each model subclasses `Observation` (`observation_model.py`) and is tagged with
`@register_observation_model(ObservationModelType.X)`; `space()` declares the
Gymnasium space and `observe()` returns one observation in it. The registry is
the whole interface -- the runner names an `ObservationModelType` and never a
class, so an image-based or graph-based model drops in beside the numeric one.

Shipped: `numeric_observation`, a flat vector of normalised lane, car and
reservation features.

The registry is populated on first lookup, not on import: `get_*` calls this
package's `load_plugins()`, which imports every module in it so the decorators
run. Keeping it off the import path means naming a type costs nothing.
"""

from umlsl_sim.rl.plugin_loader import package_loader

#: Imports every module in this package so the decorators run and the registry
#: is populated. Called by the registry lookup, not on import -- see
#: `rl.plugin_loader`.
load_plugins = package_loader(__name__, __file__)
