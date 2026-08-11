"""Draws the simulation world into a sub-rectangle of the control window.

The existing :class:`~umlsl_sim.gui.scene_drawer.GameDrawer` produces pyglet
shapes in scene coordinates (0..WINDOW_WIDTH, 0..WINDOW_HEIGHT). Here we place
those shapes inside an arbitrary on-screen viewport by temporarily swapping the
window's view matrix (scene -> viewport pixels) and clipping with a scissor box,
so the map, cars and goals render exactly like the standalone simulation but
embedded next to the control panel.

The static map (roads, lane lines, arrows) is cached and only rebuilt when the
road network changes; goals and cars are rebuilt every frame.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import pyglet
from pyglet import shapes
from pyglet.gl import GL_SCISSOR_TEST, glDisable, glEnable, glScissor
from pyglet.math import Mat4, Vec3

from umlsl_sim.constants import WINDOW_HEIGHT, WINDOW_WIDTH
from umlsl_sim.gui.scene_drawer import GameDrawer
from umlsl_sim.gui.control import theme

SCENE_W = WINDOW_WIDTH
SCENE_H = WINDOW_HEIGHT

Viewport = Tuple[float, float, float, float]  # (x, y, w, h) in window (logical) coords


def fit_transform(viewport: Viewport) -> Mat4:
    """View matrix that letterboxes the scene into ``viewport``."""
    vx, vy, vw, vh = viewport
    scale = min(vw / SCENE_W, vh / SCENE_H)
    ox = vx + (vw - SCENE_W * scale) / 2
    oy = vy + (vh - SCENE_H * scale) / 2
    return Mat4.from_translation(Vec3(ox, oy, 0)) @ Mat4.from_scale(Vec3(scale, scale, 1))


class SceneRenderer:
    def __init__(self, window) -> None:
        self.window = window
        self._roads = None
        self._map_batch: Optional[pyglet.graphics.Batch] = None
        self._map_shapes: List = []

    def _ensure_map(self, roads) -> None:
        if roads is self._roads and self._map_batch is not None:
            return
        self._roads = roads
        self._map_batch = pyglet.graphics.Batch()
        self._map_shapes = [
            shapes.Rectangle(0, 0, SCENE_W, SCENE_H, color=theme.SCENE_BG)
        ]
        self._map_shapes += GameDrawer.draw_map(roads)
        for sh in self._map_shapes:
            sh.batch = self._map_batch

    def draw(self, viewport: Viewport, world, flash_count: int, show_reservation: bool) -> None:
        if world is None:
            return
        roads, cars, reservation_management = world
        self._ensure_map(roads)

        dyn_batch = pyglet.graphics.Batch()
        dyn_shapes: List = []
        dyn_shapes += GameDrawer.draw_goals(cars)
        dyn_shapes += GameDrawer.draw_cars(cars, flash_count, show_reservation, reservation_management)
        for sh in dyn_shapes:
            sh.batch = dyn_batch

        vx, vy, vw, vh = viewport
        ratio = self.window.get_pixel_ratio()
        old_view = self.window.view
        glEnable(GL_SCISSOR_TEST)
        glScissor(int(vx * ratio), int(vy * ratio), int(vw * ratio), int(vh * ratio))
        self.window.view = fit_transform(viewport)
        self._map_batch.draw()
        dyn_batch.draw()
        self.window.view = old_view
        glDisable(GL_SCISSOR_TEST)

        del dyn_shapes  # hold refs until after draw
