"""One car's outstanding lane change, in either of its two phases.

A lane change is registered as a *claim* on the target segment and turns into
a *reservation* on it CLAIM_TIME ticks later (`Car.check_reservation` does the
conversion, and sets `committed`). The record is the same object throughout:
`committed` is what separates the phase the holder may still walk away from
from the one it may not.

Both phases occupy the target segment as far as every *other* car is concerned
-- `ReservationManagement.get_cars_changing_into_segment` reports them alike,
and the safety rules in `simulation.safety_checks` keep clear of both. What the
phases differ in is what the holder itself may do: withdraw a claim, or see a
committed change through.
"""

from dataclasses import dataclass

from umlsl_sim.simulation.road_network.road_network import LaneSegment


@dataclass
class LaneChangeClaim:
    """The target segment of a lane change, and where it is in the manoeuvre.

    Attributes:
        segment (LaneSegment): The segment being claimed -- the one abreast of
            the car's current segment, in the lane it is moving towards.
        claimed_at (int): The car's own tick counter when the claim was
            registered. Every deadline in the manoeuvre is measured from it.
        committed (bool): False while the claim may still be withdrawn, True
            once it has become a reservation.
    """

    segment: LaneSegment
    claimed_at: int
    committed: bool = False
