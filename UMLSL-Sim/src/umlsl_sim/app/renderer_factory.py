"""Binds the presentation port to a concrete renderer.

This is the composition root's one job with respect to the GUI: everything
below it asks `simulation.ports.create_renderer(...)` for a renderer and gets
whichever implementation was registered here. Swapping pyglet for something
else is a change to this file alone.
"""

from __future__ import annotations

from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.simulation.ports import NullRenderer, Renderer, set_renderer_factory


def create_renderer(render_mode: RenderMode, show_reservations: bool = True) -> Renderer:
    """A pyglet renderer for GUI runs, a no-op renderer for headless ones.

    pyglet is imported only on the GUI branch, so a headless run -- training, a
    benchmark, a machine with no display -- never needs the GUI dependency.
    """
    if render_mode is RenderMode.GUI:
        from umlsl_sim.gui.pyglet_renderer import PygletRenderer

        return PygletRenderer(show_reservations=show_reservations)
    return NullRenderer()


def register() -> None:
    """Make `create_renderer` the renderer factory for this process."""
    set_renderer_factory(create_renderer)
