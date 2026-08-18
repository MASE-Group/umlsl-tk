from typing import Dict, List
from umlsl_sim.simulation.road_network.road_network import Segment

class SegmentOccupancyTracker:
    def __init__(self):
        self.__segment_occupancy_dict: Dict[Segment, List[str]] = dict()


    def add_segment_occupancy(self, segment: Segment, car_id: str) -> None:
        if segment not in self.__segment_occupancy_dict:
            self.__segment_occupancy_dict[segment] = [car_id]
        else:
            self.__segment_occupancy_dict[segment].append(car_id)


    def remove_segment_occupancy(self, segment: Segment, car_id: str) -> None:
        self.__segment_occupancy_dict[segment].remove(car_id)


    def get_cars_on_segment(self, segment: Segment) -> List[str]:
        """Ids of the cars occupying `segment`, in the order they claimed it.

        A read only reads: an unoccupied segment gives back an empty list
        without being recorded as a key, so the safety checks (which query
        every segment of a projected route, most of them empty) cannot grow the
        occupancy table by asking about it.
        """
        return list(self.__segment_occupancy_dict.get(segment, ()))
    

    def reset(self) -> None:
        self.__segment_occupancy_dict.clear()