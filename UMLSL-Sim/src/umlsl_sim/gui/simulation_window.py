import pyglet
from pyglet import shapes
from pyglet.math import Mat4, Vec3
from typing import List, Optional, Tuple, Union
from umlsl_sim.config.logic_constants import DEFAULT_WORLD_SIZE
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.road_network.road_network import Point, Road
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.gui.camera import WHEEL_ZOOM_STEP, Camera
from umlsl_sim.gui.colors.map_colors import OUTSIDE_WORLD, PALE_GREEN
from umlsl_sim.gui.shape_batch import ShapeBatchRenderer
from umlsl_sim.gui.scene_drawer import GameDrawer
from umlsl_sim.gui.gui_constants import (
    FLASH_CYCLE,
    TIME_PER_FRAME,
)

#: Largest share of the screen the window opens with, in each direction.
SCREEN_SHARE = 0.85
#: Smallest window, in window units: the world is fitted into whatever is left.
MIN_WINDOW_SIZE = (320, 200)


class GameWindow(pyglet.window.Window):
    """The standalone simulation window.

    The world is fitted into the window (`Camera`): a scenario of any size opens
    in full, at as many pixels per block as the screen allows. The user can
    scroll to zoom about the mouse, drag to pan, and press F to see the whole
    world again; SPACE pauses.
    """

    def __init__(
            self, 
            cars: List[Car],
            roads: List[Road],
            reservation_management: ReservationManagement,
            show_reservations: bool,
            world_size: Optional[Tuple[int, int]] = None,
            ) -> None:
        """
        Initialize the CarsWindow.

        Args:
            cars: The cars to draw.
            roads: The roads to draw.
            reservation_management: The reservations, drawn when `show_reservations`.
            show_reservations: Whether to draw reserved space.
            world_size: Width and height of the world, in pixels; None for the default world.
        """
        super().__init__(caption="UMLSL-Sim", resizable=True)
        self.world_size: Tuple[int, int] = tuple(world_size) if world_size is not None else DEFAULT_WORLD_SIZE
        self.camera = Camera()
        self._open_at_world_size()
        self.renderer = ShapeBatchRenderer(self)
        
        self.cars = cars
        self.roads = roads
        self.map_shapes: List[Union[shapes.Line, shapes.Rectangle]] = self._draw_map()

        self.reservation_management = reservation_management

        self.show_reservations: bool = show_reservations

        self._test_results = None

        self.pause: bool = False
        self.flash_count: int = 0

    def _open_at_world_size(self) -> None:
        """Size the window to show one world pixel per screen pixel, as far as the screen allows, and centre it."""
        ratio = self.get_pixel_ratio()
        screen = self.display.get_default_screen()
        width, height = self.world_size[0] / ratio, self.world_size[1] / ratio
        shrink = min(1.0, SCREEN_SHARE * screen.width / width, SCREEN_SHARE * screen.height / height)
        window_width = max(MIN_WINDOW_SIZE[0], int(width * shrink))
        window_height = max(MIN_WINDOW_SIZE[1], int(height * shrink))

        self.set_size(window_width, window_height)
        self.set_minimum_size(*MIN_WINDOW_SIZE)
        self.set_location((screen.width - window_width) // 2, (screen.height - window_height) // 2)

    def _draw_map(self) -> List[Union[shapes.Line, shapes.Rectangle]]:
        # the world's own background, so that zoomed out its edges show
        background = shapes.Rectangle(0, 0, self.world_size[0], self.world_size[1], color=PALE_GREEN)
        return [background] + GameDrawer.draw_map(self.roads, self.world_size)

    def reset_model(self, cars: List[Car], roads: List[Road], world_size: Optional[Tuple[int, int]] = None) -> None:
        self.cars = cars
        self.roads = roads
        new_size = tuple(world_size) if world_size is not None else DEFAULT_WORLD_SIZE
        if new_size != self.world_size:
            self.world_size = new_size
            self.camera.reset()
        self.map_shapes = self._draw_map()
        self.flash_count = 0
        self.pause = False
        self._test_results = None

    @property
    def test_results(self) -> None | List[Tuple[bool, str]]:
        return self._test_results
    
    @test_results.setter
    def test_results(self, value: None | List[Tuple[bool, str]]) -> None:
        if value is not None:
            self._test_results = value

    @property
    def _scene_viewport(self) -> Tuple[float, float, float, float]:
        # the default projection spans get_size(), whatever the platform's DPI scaling
        return 0.0, 0.0, float(self.width), float(self.height)

    def on_draw(self) -> None:
        """
        Handle the draw event to update the window content.
        """
        self.flash_count += TIME_PER_FRAME if not self.flash_count >= FLASH_CYCLE else -self.flash_count
        
        game_shapes = []
        game_shapes += self.map_shapes
        game_shapes += GameDrawer.draw_goals(self.cars)
        game_shapes += GameDrawer.draw_cars(self.cars, self.flash_count, self.show_reservations, self.reservation_management)

        scale, offset_x, offset_y = self.camera.transform(self._scene_viewport, self.world_size)
        old_view = self.view
        self.view = Mat4.from_translation(Vec3(offset_x, offset_y, 0)) @ Mat4.from_scale(Vec3(scale, scale, 1))
        self.renderer.render(game_shapes, clear_color=OUTSIDE_WORLD)
        self.view = old_view

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        """
        Handle key press events.
        Space key toggles pause state; F shows the whole world again.

        Args:
            symbol (int): The key symbol pressed.
            modifiers (int): The modifier keys pressed.
        """
        if symbol == pyglet.window.key.SPACE:
            self.pause = not self.pause
        elif symbol == pyglet.window.key.F:
            self.camera.reset()

    def on_mouse_scroll(self, x: int, y: int, scroll_x: float, scroll_y: float) -> None:
        if scroll_y:
            self.camera.zoom_at(self._scene_viewport, self.world_size, x, y, WHEEL_ZOOM_STEP ** scroll_y)

    def on_mouse_drag(self, x: int, y: int, dx: int, dy: int, buttons: int, modifiers: int) -> None:
        if buttons & pyglet.window.mouse.LEFT:
            self.camera.pan(self._scene_viewport, self.world_size, dx, dy)
