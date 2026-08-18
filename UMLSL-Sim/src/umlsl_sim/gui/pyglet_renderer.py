"""The pyglet implementation of `simulation.ports.Renderer`.

This is the only place where the traffic logic's presentation port meets a GUI
toolkit. Everything above it -- the runners, the Gymnasium environment, the
history playback -- talks to the port, so replacing pyglet means writing one
more class with these five methods and registering it (see
`umlsl_sim.app.renderer_factory`).
"""

from __future__ import annotations

import time
from typing import Callable, List

from umlsl_sim.gui.gui_constants import TIME_PER_FRAME


class PygletRenderer:
    """Draws the simulation in a pyglet window.

    The window is created on the first `bind` rather than in `__init__`, so
    constructing a renderer is free and a run that never binds a world -- an
    aborted training run, say -- never opens a window.
    """

    def __init__(self, show_reservations: bool = True) -> None:
        self.show_reservations = show_reservations
        self.window = None

    # --- Renderer port ------------------------------------------------------

    def bind(self, cars: List, roads: List, reservation_management=None) -> None:
        if self.window is None:
            from umlsl_sim.gui.simulation_window import GameWindow

            self.window = GameWindow(cars, roads, reservation_management, self.show_reservations)
        else:
            self.window.reset_model(cars, roads)
            if reservation_management is not None:
                self.window.reservation_management = reservation_management

    def draw_frame(self) -> None:
        import pyglet

        if self.window is None:
            return
        self.window.dispatch_events()
        self.window.on_draw()
        pyglet.clock.tick()
        self.window.flip()
        time.sleep(1.0 / TIME_PER_FRAME)

    def run_loop(self, update: Callable[[float], None],
                 interval: "float | None" = None) -> None:
        import pyglet

        pyglet.clock.unschedule(update)
        pyglet.clock.schedule_interval(update, interval if interval is not None
                                       else 1 / TIME_PER_FRAME)
        pyglet.app.run()

    def stop_loop(self) -> None:
        import pyglet

        pyglet.app.exit()

    def close(self) -> None:
        if self.window is not None:
            self.window.close()
            self.window = None

    # --- Pause state --------------------------------------------------------
    #
    # The window owns it: SPACE toggles pause in `GameWindow.on_key_press`, and
    # a runner sets it when an episode ends. Before the window exists there is
    # nothing to pause, so the fallback is "running".

    @property
    def paused(self) -> bool:
        return bool(self.window.pause) if self.window is not None else False

    @paused.setter
    def paused(self, value: bool) -> None:
        if self.window is not None:
            self.window.pause = value
