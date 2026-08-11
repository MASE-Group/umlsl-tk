from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.simulation.controllers.abstract_simulation_controller import AbstractGameController
from umlsl_sim.simulation.controllers.simulation_controller import GameController
from umlsl_sim.gui.render_mode import RenderMode

if __name__ == '__main__':
    
    scenario = load_scenario("TWO_CROSSINGS")

    controller: AbstractGameController = GameController(
        roads=scenario["roads"],
        players=scenario["players"],
        render_mode=RenderMode.GUI,
        show_reservation=True,
        predefined_cars=scenario["predefined_cars"],
    )
    
    controller.run()