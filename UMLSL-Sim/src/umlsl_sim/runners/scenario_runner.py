"""Runs NPC traffic on a road network until the episode ends.

The loop is the same whether or not anyone is watching: `run` hands `_update` to
the renderer, and the renderer decides how often to call it. A GUI renderer
paces it on the pyglet clock and lets the user pause with SPACE; the headless
renderer calls it as fast as it can and never pauses. There is no `if gui:`
here, and nothing in this module -- not even a constant -- comes from the GUI.
"""

from typing import List

from umlsl_sim.runners.runner import SimulationRunner
from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.factories.car_spec import CarSpec
from umlsl_sim.simulation.ports import CarControllerFactory
from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.simulation.traffic_environment import TrafficEnv


class ScenarioRunner(SimulationRunner):
    """Input: roads, a car count and an optional list of predefined cars.
    Output: a run of `TrafficEnv` played to its end state.
    """

    def __init__(
            self,
            roads: List[Road],
            players: int,
            render_mode: RenderMode,
            show_reservation: bool = True,
            predefined_cars: None | List[CarSpec] = None,
            npc_controller_factory: None | CarControllerFactory = None,
            ):

        super().__init__(roads, players, render_mode, show_reservation)

        self.game_model: TrafficEnv = TrafficEnv(
            roads=self.roads,
            players=self.players,
            predefined_cars=predefined_cars,
            npc_controller_factory=npc_controller_factory,
        )
        self.done = None

    def run(self) -> None:
        self._start_new_game()
        self.renderer.run_loop(self._update)

        self.game_model.current_state()

    def _start_new_game(self) -> None:
        self.game_model.reset()
        self.done = None
        self.renderer.bind(
            self.game_model.cars,
            self.game_model.roads,
            self.game_model.reservation_management,
        )

    def _update(self, delta_time: float) -> None:
        """One tick of the run, called by whichever renderer owns the loop.

        When an episode ends, a watched run holds the final frame until the user
        unpauses (SPACE) and then starts the next episode; a headless run has
        nothing to hold, so it ends the loop and `run` returns.
        """
        if self.done is not None:
            if self.render_mode is RenderMode.GUI:
                if not self.renderer.paused:
                    self._start_new_game()
            else:
                self.renderer.stop_loop()
            return

        if self.renderer.paused:
            return

        self.done = self.game_model.play_step()
        if self.done is not None:
            self.renderer.paused = True
