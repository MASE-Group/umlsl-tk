from typing import Dict, List
from umlsl_sim.simulation.road_network.road_network import Segment, CrossingSegment, SegmentInfo

from umlsl_sim.simulation.reservations.car_reservation_store import CarReservationStore
from umlsl_sim.simulation.reservations.lane_change_claim import LaneChangeClaim
from umlsl_sim.simulation.reservations.segment_occupancy_tracker import SegmentOccupancyTracker

class ReservationManagement:
    def __init__(self):
        self.__car_reservation_store: CarReservationStore = CarReservationStore()
        self.__segment_occupancy_tracker: SegmentOccupancyTracker = SegmentOccupancyTracker()

        self.__lane_change_claims: Dict[str, LaneChangeClaim | None] = {}

    def add_car_reservation(self, car_id: str, segment_info: SegmentInfo) -> None:
        self.__car_reservation_store.add_reservation(car_id, segment_info)
        self.__segment_occupancy_tracker.add_segment_occupancy(segment_info.segment, car_id)


    def get_car_reservation(self, car_id: str, index: int) -> SegmentInfo:
        return self.__car_reservation_store.get_reserved_segment(car_id, index)


    def pop_car_reservation(self, car_id: str, index: int) -> SegmentInfo:
        segment_info = self.__car_reservation_store.pop_reservation(car_id, index)
        self.__segment_occupancy_tracker.remove_segment_occupancy(segment_info.segment, car_id)

        if isinstance(segment_info.segment, CrossingSegment):
            segment_info.segment.crossing_segment_state.pop_time_to_leave(car_id)

        return segment_info
    
    def get_cars_on_segment(self, segment: Segment) -> List[str]:
        return self.__segment_occupancy_tracker.get_cars_on_segment(segment)

    def get_lane_change_claim(self, car_id: str) -> LaneChangeClaim | None:
        """The lane change this car has outstanding, in either phase, or None.

        None covers both "this car registered a change and it has since been
        cleared" and "this car never registered one" -- every caller already
        treats the absent case that way, and a car that has never changed lane
        is the ordinary case rather than a lookup error.

        The record is live: committing a claim mutates the object this returns.
        """
        return self.__lane_change_claims.get(car_id)

    def get_cars_changing_into_segment(self, segment: Segment) -> List[str]:
        """Ids of the cars whose lane change targets `segment`.

        Claims and committed changes are reported alike: an uncommitted claim
        is space taken as far as everybody but its holder is concerned.
        """
        return [car_id for car_id, claim in self.__lane_change_claims.items()
                if claim is not None and claim.segment is segment]

    def set_lane_change_claim(self, car_id: str, claim: LaneChangeClaim) -> None:
        self.__lane_change_claims[car_id] = claim

    def commit_lane_change_claim(self, car_id: str) -> None:
        """Turn this car's claim into a reservation it can no longer withdraw.

        Does nothing when the car holds no claim, so a caller that has just
        read the claim does not have to guard against it disappearing.
        """
        claim = self.__lane_change_claims.get(car_id)
        if claim is not None:
            claim.committed = True

    def remove_lane_change_claim(self, car_id: str) -> None:
        """Drop this car's claim -- withdrawn, completed, or died holding it."""
        self.__lane_change_claims[car_id] = None

    def update_car_reservation_begin(self, car_id: str, index: int, begin: int) -> None:
        self.__car_reservation_store.update_begin(car_id, index, begin)

    def update_car_reservation_end(self, car_id: str, index: int, end: int) -> None:
        self.__car_reservation_store.update_end(car_id, index, end)

    def update_car_reservation_turn(self, car_id: str, index: int, turn: bool) -> None:
        self.__car_reservation_store.update_turn(car_id, index, turn)

    def get_car_reservations(self, car_id: str) -> List[SegmentInfo]:
        return self.__car_reservation_store.get_reserved_segments(car_id)
    
    def get_car_reservations_view(self, car_id: str) -> List[SegmentInfo]:
        """Live list — caller must not append/pop, but may mutate SegmentInfo fields."""
        return self.__car_reservation_store.get_reserved_segments_view(car_id)

    def reset(self) -> None:
        self.__car_reservation_store.reset()
        self.__segment_occupancy_tracker.reset()
        self.__lane_change_claims.clear()