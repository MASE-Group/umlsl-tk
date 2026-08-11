from abc import ABC, abstractmethod
from typing import List

from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.gui.render_mode import RenderMode

class AbstractGameController(ABC):
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
        

    @abstractmethod
    def run(self) -> None:
        ...