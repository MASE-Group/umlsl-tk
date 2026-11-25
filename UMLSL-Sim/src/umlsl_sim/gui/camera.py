"""How the world is placed in a viewport: fitted to it, then zoomed and panned by the user.

A scenario's world can have any size (`TrafficEnv.world_size`), so no window shows
it one pixel per world unit any more. By default the whole world is fitted into
the viewport, centred, with its aspect ratio kept; the user can then zoom about
the mouse (without limit outwards, see `MIN_ZOOM`) and drag to pan, and reset
back to the fitted view. The traffic logic's unit, `BLOCK_SIZE`, never changes:
only the number of screen pixels a block is drawn with does.

This module only does the arithmetic, so it needs no GUI toolkit and is tested on
its own. A window turns `transform` into its view matrix.
"""
from __future__ import annotations

from typing import Optional, Tuple

from umlsl_sim.config.logic_constants import BLOCK_SIZE

Viewport = Tuple[float, float, float, float]
"""``(x, y, width, height)`` of the viewport, in window coordinates."""

WorldSize = Tuple[int, int]
"""Width and height of the world, in world units (pixels of the traffic logic)."""

MIN_ZOOM = 1e-3
"""Smallest zoom, relative to the fitted view. Only keeps the view from degenerating."""

MAX_BLOCK_PIXELS = 400.0
"""Largest number of window units a block may be drawn with, however far the user zooms in."""

WHEEL_ZOOM_STEP = 1.15
"""Zoom factor of one scroll-wheel click."""


class Camera:
    """The user's zoom and pan on top of the fitted view of a world.

    Attributes:
        zoom: Scale relative to the fitted view; 1.0 shows the whole world.
        center: World point shown at the viewport's centre, or None for the
            world's own centre.
    """

    def __init__(self) -> None:
        self.zoom: float = 1.0
        self.center: Optional[Tuple[float, float]] = None

    def reset(self) -> None:
        """Back to the fitted view: the whole world, centred."""
        self.zoom = 1.0
        self.center = None

    @property
    def is_fitted(self) -> bool:
        return self.zoom == 1.0 and self.center is None

    # --- the transform ------------------------------------------------------

    @staticmethod
    def fit_scale(viewport: Viewport, world_size: WorldSize) -> float:
        """Window units per world unit that make the whole world fit the viewport."""
        _, _, vw, vh = viewport
        width, height = world_size
        return min(vw / width, vh / height)

    def scale(self, viewport: Viewport, world_size: WorldSize) -> float:
        return self.fit_scale(viewport, world_size) * self.zoom

    def _center(self, world_size: WorldSize) -> Tuple[float, float]:
        if self.center is not None:
            return self.center
        return world_size[0] / 2, world_size[1] / 2

    def transform(self, viewport: Viewport, world_size: WorldSize) -> Tuple[float, float, float]:
        """``(scale, offset_x, offset_y)``: a world point p is drawn at ``p * scale + offset``."""
        vx, vy, vw, vh = viewport
        scale = self.scale(viewport, world_size)
        cx, cy = self._center(world_size)
        return scale, vx + vw / 2 - cx * scale, vy + vh / 2 - cy * scale

    def to_world(self, viewport: Viewport, world_size: WorldSize, x: float, y: float) -> Tuple[float, float]:
        """The world point drawn at window point ``(x, y)``."""
        scale, ox, oy = self.transform(viewport, world_size)
        return (x - ox) / scale, (y - oy) / scale

    # --- user input ---------------------------------------------------------

    def zoom_at(self, viewport: Viewport, world_size: WorldSize, x: float, y: float, factor: float) -> None:
        """Zoom by ``factor`` (> 1 zooms in), keeping the world point under ``(x, y)`` where it is."""
        fit = self.fit_scale(viewport, world_size)
        max_zoom = MAX_BLOCK_PIXELS / BLOCK_SIZE / fit
        new_zoom = min(max(self.zoom * factor, MIN_ZOOM), max(max_zoom, 1.0))
        if new_zoom == self.zoom:
            return
        wx, wy = self.to_world(viewport, world_size, x, y)
        vx, vy, vw, vh = viewport
        self.zoom = new_zoom
        scale = fit * new_zoom
        self.center = (wx - (x - (vx + vw / 2)) / scale, wy - (y - (vy + vh / 2)) / scale)

    def pan(self, viewport: Viewport, world_size: WorldSize, dx: float, dy: float) -> None:
        """Move the world by ``(dx, dy)`` window units, as dragging it does."""
        scale = self.scale(viewport, world_size)
        cx, cy = self._center(world_size)
        self.center = (cx - dx / scale, cy - dy / scale)
