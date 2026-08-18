"""The interfaces the simulation is driven through.

The simulation layer owns the traffic logic and nothing else: it does not know
how a car decides what to do, and it does not know whether anyone is watching.
Both of those arrive through the protocols below, so an alternative
implementation of either is a drop-in replacement -- it only has to match the
shape declared here, not inherit from anything or live in a particular package.

Two ports are defined:

* `CarController` -- what the environment asks an NPC's driver for each tick.
  Implemented in `umlsl_sim.control` (the A* controller); an alternative
  planner is supplied through `TrafficEnv(npc_controller_factory=...)`.
* `Renderer` -- how a run is shown. Implemented in `umlsl_sim.gui` (pyglet) and
  by `NullRenderer` below (headless). The concrete one is chosen by the
  composition root, which registers a factory through `set_renderer_factory`;
  nothing in this layer or in `umlsl_sim.rl` ever imports a GUI toolkit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Protocol, Tuple, runtime_checkable

from umlsl_sim.config.render_mode import RenderMode

if TYPE_CHECKING:
    from umlsl_sim.simulation.car import Car
    from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
    from umlsl_sim.simulation.road_network.road_network import Road


# --- Car control -------------------------------------------------------------

@runtime_checkable
class CarController(Protocol):
    """Decides one car's action for the current tick.

    Input:  the car, the other cars and the reservation book, all supplied at
            construction time and read live thereafter.
    Output: `get_action()` -> (acceleration, lane_change), where acceleration is
            in [-MAX_DEC, MAX_ACC] and lane_change is one of NO_LANE_CHANGE /
            LEFT_LANE_CHANGE / RIGHT_LANE_CHANGE.
    """

    def get_action(self) -> Tuple[int, int]:
        ...


#: How `TrafficEnv` builds a controller for each NPC it spawns.
CarControllerFactory = Callable[
    ["Car", List["Car"], "ReservationManagement"], CarController
]


# --- Presentation ------------------------------------------------------------

@runtime_checkable
class Renderer(Protocol):
    """Shows a running simulation. Every method is optional to *use*, but a
    renderer must provide all of them.

    Input:  a world (cars, roads, reservations) through `bind`, then a redraw
            request per frame.
    Output: pixels, or nothing at all -- see `NullRenderer`.

    `paused` is read *and written* by the runners: the pyglet renderer sets it
    from a key press, and a runner sets it when an episode ends.
    """

    paused: bool

    def bind(self,
             cars: List["Car"],
             roads: List["Road"],
             reservation_management: "ReservationManagement | None" = None) -> None:
        """Attach (or re-attach, after a reset) the world to be drawn."""
        ...

    def draw_frame(self) -> None:
        """Draw one frame now, pacing itself to the renderer's frame rate."""
        ...

    def run_loop(self, update: Callable[[float], None],
                 interval: "float | None" = None) -> None:
        """Call `update(dt)` repeatedly until `stop_loop` is called.

        Owning the loop is the renderer's job, because a GUI toolkit insists on
        owning it; `NullRenderer` provides the same contract without one. The
        pacing is the renderer's too: `interval=None` means "your natural
        rate", which is a frame period for a window and no delay at all for a
        headless run, so a runner never has to know which it is talking to.
        """
        ...

    def stop_loop(self) -> None:
        """End the loop started by `run_loop`."""
        ...

    def close(self) -> None:
        """Release whatever `bind` acquired. Safe to call more than once."""
        ...


class NullRenderer:
    """The headless `Renderer`: draws nothing, still runs the loop.

    A headless run is not a special case of a watched one -- it is the same
    runner with this renderer, which is why the runners have no `if gui:`
    branches around stepping.
    """

    def __init__(self) -> None:
        self.paused = False
        self._running = False

    def bind(self, cars, roads, reservation_management=None) -> None:
        pass

    def draw_frame(self) -> None:
        pass

    def run_loop(self, update: Callable[[float], None],
                 interval: "float | None" = None) -> None:
        self._running = True
        dt = interval if interval is not None else 0.0
        while self._running:
            update(dt)

    def stop_loop(self) -> None:
        self._running = False

    def close(self) -> None:
        self._running = False


#: Builds the renderer for a run. Registered by the composition root.
RendererFactory = Callable[[RenderMode, bool], Renderer]


def _null_renderer_factory(render_mode: RenderMode, show_reservations: bool) -> Renderer:
    if render_mode is RenderMode.GUI:
        raise RuntimeError(
            "RenderMode.GUI was requested but no renderer factory is registered. "
            "Entry points under umlsl_sim.app register one on import; a program "
            "that builds its own composition root calls "
            "umlsl_sim.simulation.ports.set_renderer_factory(...) instead."
        )
    return NullRenderer()


_renderer_factory: RendererFactory = _null_renderer_factory


def set_renderer_factory(factory: RendererFactory) -> None:
    """Choose the renderer implementation for this process.

    Swapping the GUI for another one -- a web view, a video recorder, a test
    double -- is this single call; no module below the composition root names a
    concrete renderer.
    """
    global _renderer_factory
    _renderer_factory = factory


def create_renderer(render_mode: RenderMode, show_reservations: bool = True) -> Renderer:
    """The renderer for `render_mode`, from whichever factory is registered."""
    return _renderer_factory(render_mode, show_reservations)
