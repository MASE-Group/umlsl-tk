from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple

from umlsl_sim.constants import PRIORITY_REORDER_TICKS, PRIORITY_WITHDRAW_TICKS


class ClaimUpdate(Enum):
    """The effect of one call to `IntersectionState.renew_car_priority`."""

    HELD = 1        # the claim survived the tick unchanged
    REORDERED = 2   # the claim was moved behind every earlier claimant
    WITHDRAWN = 3   # the claim is gone; the car must claim again before entering


@dataclass
class _Claim:
    """One car's outstanding claim on an intersection."""

    priority: int           # crossing order; a smaller value crosses first
    claimed_at: int         # tick the claim was first registered, for diagnostics
    stalled_for: int = 0    # consecutive ticks the claimant made no progress
    reordered: bool = False # already demoted once during the current stall


class IntersectionState:
    """The right-of-way queue of a single intersection.

    A car approaching the intersection registers a *claim* whose priority is
    the tick it claimed on, and may enter only while no other claimant holds a
    strictly earlier priority -- a first-come, first-served crossing order in
    which cars that claim on the same tick do not block one another.

    A claim is a lease rather than a permanent grant. Its holder calls
    `renew_car_priority` once per tick, reporting whether it made progress:

    * progress resets the lease;
    * after PRIORITY_REORDER_TICKS ticks without progress the claim is
      *reordered* to the current tick, putting it behind every car that is
      still approaching normally and releasing the ones it was holding up,
      while keeping the claimant in the queue ahead of later arrivals;
    * after PRIORITY_WITHDRAW_TICKS it is *withdrawn* altogether. This is the
      `wd cc(C)` action of the abstract crossing controller, bounded in time
      here rather than left to the claimant's discretion. The car claims again
      on the next tick it is still approaching, at the back of the queue.

    Those two bounds are what stops a cyclic wait from persisting: a car that
    cannot move never holds the intersection closed for longer than
    PRIORITY_WITHDRAW_TICKS ticks, so a ring of cars each waiting on the next
    always breaks. Entry itself stays governed by the reservation and
    time-to-leave rules, which is why loosening the ordering costs no collision
    freedom -- a reordered car still cannot enter a crossing segment that
    somebody else holds.
    """

    def __init__(self) -> None:
        self.__claims: Dict[str, _Claim] = dict()


    def get_car_priority(self, car_id: str) -> None | int:
        """The car's place in the crossing order, or None if it holds no claim."""
        claim = self.__claims.get(car_id)
        return None if claim is None else claim.priority


    def add_car_priority(self, car_id: str, time: int) -> None:
        """Register a claim for `car_id`, taking `time` as its place in the queue.

        Does nothing when the car already holds a claim, so a car that keeps
        approaching keeps the place it has already earned.
        """
        if car_id in self.__claims:
            return
        self.__claims[car_id] = _Claim(priority=time, claimed_at=time)


    def renew_car_priority(self, car_id: str, time: int,
                           made_progress: bool) -> ClaimUpdate:
        """Age `car_id`'s claim by one tick, reporting what became of it.

        A car that holds no claim has nothing to renew and is reported as
        WITHDRAWN.
        """
        claim = self.__claims.get(car_id)
        if claim is None:
            return ClaimUpdate.WITHDRAWN

        if made_progress:
            claim.stalled_for = 0
            claim.reordered = False
            return ClaimUpdate.HELD

        claim.stalled_for += 1

        if claim.stalled_for >= PRIORITY_WITHDRAW_TICKS:
            del self.__claims[car_id]
            return ClaimUpdate.WITHDRAWN

        if claim.stalled_for >= PRIORITY_REORDER_TICKS and not claim.reordered:
            claim.priority = time
            claim.reordered = True
            return ClaimUpdate.REORDERED

        return ClaimUpdate.HELD


    def outranked(self, car_id: str) -> bool:
        """True if another claimant must cross this intersection first.

        A car holding no claim is never outranked: the ordering is expressed
        over claims, and a car without one is governed by the reservation and
        time-to-leave rules alone.
        """
        claim = self.__claims.get(car_id)
        if claim is None:
            return False
        return any(other.priority < claim.priority
                   for other_id, other in self.__claims.items()
                   if other_id != car_id)


    def pop_car_priority(self, car_id: str) -> None | int:
        """Withdraw `car_id`'s claim, returning the place it held."""
        claim = self.__claims.pop(car_id, None)
        return None if claim is None else claim.priority


    def get_priority_items(self) -> List[Tuple[str, int]]:
        """(car_id, priority) for every outstanding claim."""
        return [(car_id, claim.priority) for car_id, claim in self.__claims.items()]


    def reset(self) -> None:
        self.__claims.clear()
