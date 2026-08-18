"""Constants that define the traffic model, kept apart from any consumer of it.

Nothing in this package imports another `umlsl_sim` module, so every other
module may depend on it and none of them are coupled through it.

* `logic_constants` -- the traffic logic itself: the world's coordinate space,
  the speeds and accelerations a car may take, the lane-change encoding.
* `simulation_constants` -- how a *run* of that logic is scored and terminated:
  the winning score, the crossing-claim lease, the deadlock window.
* `render_mode` -- whether a run is watched or headless. It lives here rather
  than in `gui` so that choosing a mode does not drag in a GUI toolkit.

Import the individual modules, not this package: `from umlsl_sim.config.logic_constants
import BLOCK_SIZE`. The split is the documentation, and a star-import erases it.
"""
