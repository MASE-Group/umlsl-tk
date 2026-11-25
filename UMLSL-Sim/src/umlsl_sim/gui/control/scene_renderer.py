"""Draws the simulation world into a sub-rectangle of the control window.

The existing :class:`~umlsl_sim.gui.scene_drawer.GameDrawer` produces pyglet
shapes in world coordinates (0..width, 0..height of the scenario's world). Here
we place those shapes inside an arbitrary on-screen viewport by temporarily
swapping the window's view matrix (world -> viewport pixels) and clipping with a
scissor box, so the map, cars and goals render exactly like the standalone
simulation but embedded next to the control panel. Where in the viewport the
world goes is the :class:`~umlsl_sim.gui.camera.Camera`'s business: fitted to
the viewport by default, then zoomed and panned by the user.

The static map (roads, lane lines, arrows) is cached and only rebuilt when the
road network or the world changes; goals and cars are rebuilt every frame.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import pyglet
from pyglet import shapes
from pyglet.gl import GL_SCISSOR_TEST, glDisable, glEnable, glScissor
from pyglet.math import Mat4, Vec3

from umlsl_sim.config.logic_constants import DEFAULT_WORLD_SIZE
from umlsl_sim.gui.camera import Camera, WorldSize
from umlsl_sim.gui.scene_drawer import GameDrawer
from umlsl_sim.gui.control import theme

Viewport = Tuple[float, float, float, float]  # (x, y, w, h) in window (logical) coords


def camera_transform(camera: Camera, viewport: Viewport, world_size: WorldSize) -> Mat4:
    """View matrix that draws the world where ``camera`` puts it in ``viewport``."""
    scale, ox, oy = camera.transform(viewport, world_size)
    return Mat4.from_translation(Vec3(ox, oy, 0)) @ Mat4.from_scale(Vec3(scale, scale, 1))


def fit_transform(viewport: Viewport, world_size: WorldSize = DEFAULT_WORLD_SIZE) -> Mat4:
    """View matrix that letterboxes the whole world into ``viewport``."""
    return camera_transform(Camera(), viewport, world_size)


class SceneRenderer:
    def __init__(self, window) -> None:
        self.window = window
        self.camera = Camera()
        self._roads = None
        self._world_size: Optional[WorldSize] = None
        self._map_batch: Optional[pyglet.graphics.Batch] = None
        self._map_shapes: List = []

    def _ensure_map(self, roads, world_size: WorldSize) -> None:
        if roads is self._roads and world_size == self._world_size and self._map_batch is not None:
            return
        if world_size != self._world_size:
            self.camera.reset()  # another world: show all of it again
        self._roads = roads
        self._world_size = world_size
        self._map_batch = pyglet.graphics.Batch()
        # the world's own background, so that zoomed out its edge shows against the viewport card
        self._map_shapes = [
            shapes.Rectangle(0, 0, world_size[0], world_size[1], color=theme.SCENE_BG)
        ]
        self._map_shapes += GameDrawer.draw_map(roads, world_size)
        for sh in self._map_shapes:
            sh.batch = self._map_batch

    def _scissor_scale(self) -> Tuple[float, float]:
        """Window units -> framebuffer pixels, the space ``glScissor`` works in.

        Not ``get_pixel_ratio()``: that is the framebuffer/window-frame ratio,
        which only doubles as this conversion when pyglet reports sizes in
        window-frame units. Under the default ``dpi_scaling="platform"`` on a
        HiDPI screen it does not -- ``get_size()`` already returns framebuffer
        pixels, so the projection and every widget coordinate are in those
        pixels too, and scaling by the ratio again pushed the scissor box right
        past the viewport, cutting the left of the scene off. Deriving the
        factor from the two sizes gives 1.0 there and the true ratio wherever
        pyglet does report window-frame units.
        """
        fb_w, fb_h = self.window.get_framebuffer_size()
        return fb_w / max(self.window.width, 1), fb_h / max(self.window.height, 1)

    def draw(self, viewport: Viewport, world, flash_count: int, show_reservation: bool) -> None:
        if world is None:
            return
        roads, cars, reservation_management, world_size = world
        self._ensure_map(roads, world_size)

        dyn_batch = pyglet.graphics.Batch()
        dyn_shapes: List = []
        dyn_shapes += GameDrawer.draw_goals(cars)
        dyn_shapes += GameDrawer.draw_cars(cars, flash_count, show_reservation, reservation_management)
        for sh in dyn_shapes:
            sh.batch = dyn_batch

        vx, vy, vw, vh = viewport
        sx, sy = self._scissor_scale()
        old_view = self.window.view
        glEnable(GL_SCISSOR_TEST)
        glScissor(int(vx * sx), int(vy * sy), int(vw * sx), int(vh * sy))
        self.window.view = camera_transform(self.camera, viewport, world_size)
        self._map_batch.draw()
        dyn_batch.draw()
        self.window.view = old_view
        glDisable(GL_SCISSOR_TEST)

        del dyn_shapes  # hold refs until after draw

    # --- zoom and pan -------------------------------------------------------
    def zoom_at(self, viewport: Viewport, x: float, y: float, factor: float) -> None:
        """Zoom the shown world by ``factor`` about window point ``(x, y)``."""
        if self._world_size is not None:
            self.camera.zoom_at(viewport, self._world_size, x, y, factor)

    def pan(self, viewport: Viewport, dx: float, dy: float) -> None:
        if self._world_size is not None:
            self.camera.pan(viewport, self._world_size, dx, dy)

    def reset_view(self) -> None:
        """Show the whole world again."""
        self.camera.reset()
