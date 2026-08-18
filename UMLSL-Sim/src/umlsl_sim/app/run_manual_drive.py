from umlsl_sim.config.logic_constants import BLOCK_SIZE, WORLD_HEIGHT, WORLD_WIDTH
from umlsl_sim.simulation.road_network.road_network import  Road
from umlsl_sim.gui.manual_drive_window import CarsWindowManual

if __name__ == '__main__':

    road_bottom = Road("bottom", True, 0, 1, 0)
    road_right = Road("right", False, WORLD_WIDTH - BLOCK_SIZE, 0, 1)
    road_top = Road("top", True, WORLD_HEIGHT - BLOCK_SIZE, 0, 1)
    road_left = Road("left", False, 0, 1, 0)

    road_h1 = Road("h1", True, 145, 0, 2)
    road_h2 = Road("h2", True, 330, 3, 3)
    road_h3 = Road("h3", True, 675, 2, 0)
    road_v1 = Road("v1", False, 320, 0, 2)
    road_v2 = Road("v2", False, 680, 3, 3)
    road_v3 = Road("v3", False, 1200, 2, 0)

    # one_road = Road("r1", True, 400, 3, 3)

    roads = [road_top, road_bottom, road_left, road_right, road_h1, road_h2, road_h3, road_v1, road_v2, road_v3]
    # roads = [road_top, road_bottom, road_left, road_right, one_road]
    players = 1

    CarsWindowManual(roads)