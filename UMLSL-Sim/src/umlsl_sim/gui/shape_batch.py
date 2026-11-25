import pyglet
from pyglet import shapes
from pyglet import text
from pyglet.window import Window
from typing import List, Union
from typing import Tuple

from umlsl_sim.gui.colors.map_colors import PALE_GREEN


class ShapeBatchRenderer():
    def __init__(self, window: Window = None):
        self.window = window
        self.batch = pyglet.graphics.Batch()

    def render(self, shapes: List[Union[shapes.Line, shapes.Rectangle, shapes.Circle, text.Label]],
               clear_color: Tuple[int, int, int] = PALE_GREEN) -> None:
        pyglet.gl.glClearColor(*[c / 255 for c in clear_color], 1)
        self.window.clear()

        for shape in shapes:
            shape.batch = self.batch

        self.batch.draw()