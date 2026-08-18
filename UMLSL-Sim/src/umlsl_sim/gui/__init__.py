"""The pyglet GUI: windows, drawing, and its own constants.

Nothing below this package imports it. The simulation and the RL stack render
through `simulation.ports.Renderer`, and `gui.pyglet_renderer.PygletRenderer` is
the implementation of that port -- the single seam through which a different
front end (a web view, a video recorder, no view at all) is substituted.

What lives here:

* `gui_constants` -- window size, frame rate, lane-line offsets. Constants that
  exist only because something is being drawn; the traffic model's own numbers
  are in `umlsl_sim.config`.
* `geometry`, `scene_drawer`, `shape_batch` -- world coordinates to pyglet shapes.
* `simulation_window`, `manual_drive_window` -- the standalone windows.
* `pyglet_renderer` -- the `Renderer` port implementation.
* `control` -- the interactive control panel, a self-contained application that
  embeds a simulation next to its own widgets.
"""
