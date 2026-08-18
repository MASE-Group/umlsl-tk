"""Entry points: the scripts that run the tool, and the runners behind them.

This package is the composition root. It is the only place that knows about
every other module at once, and it is where the replaceable pieces are bound to
concrete implementations:

* the presentation port is bound to pyglet (`renderer_factory`),
* the NPC car controller is bound to the A* one (`umlsl_sim.control`).

Both bindings happen on import of this package, so any entry point below it --
`main`, `run_scenario`, `run_manual_drive`, `run_control_gui` -- gets a fully
wired application, while the layers underneath stay unaware of what they were
wired to. The run loops themselves are not here: they live in
`umlsl_sim.runners` (plain traffic) and `umlsl_sim.rl.training` (RL), and `main`
only picks between them.

Neither binding imports a GUI toolkit or the RL stack; those are pulled in only
if a run actually asks for them.
"""

from umlsl_sim.app import renderer_factory as _renderer_factory

_renderer_factory.register()
