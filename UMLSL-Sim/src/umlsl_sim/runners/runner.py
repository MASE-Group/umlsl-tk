"""What every way of running the simulator has in common.

A *runner* takes a world and drives it to completion: it owns the loop, decides
when an episode is over, and hands frames to a renderer. `ScenarioRunner` runs
NPC traffic; `umlsl_sim.rl.training.rl_runner.RLRunner` trains or replays an RL
agent. `umlsl_sim.app.main` is the only module that needs to know both exist.

The base class deliberately holds no behaviour beyond building the renderer:
subclasses share a constructor shape, not an implementation.
"""

from abc import ABC, abstractmethod
from typing import List

from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.simulation.ports import Renderer, create_renderer
from umlsl_sim.simulation.road_network.road_network import Road


class SimulationRunner(ABC):
    """Input: a road network and how to show it. Output: a completed run.

    Attributes:
        roads (List[Road]): The network to run on.
        players (int): Number of NPC cars.
        render_mode (RenderMode): Whether the run is watched.
        show_reservation (bool): Whether reserved space is drawn (GUI only).
        renderer (Renderer): Where frames go. Built through the registered
            renderer factory, so a runner never names a GUI toolkit.
    """

    def __init__(
            self,
            roads: List[Road],
            players: int,
            render_mode: RenderMode,
            show_reservation: bool,
            ):

        self.roads = roads
        self.players = players
        self.render_mode = render_mode
        self.show_reservation = show_reservation
        self.renderer: Renderer = create_renderer(render_mode, show_reservation)

    @abstractmethod
    def run(self) -> None:
        ...
