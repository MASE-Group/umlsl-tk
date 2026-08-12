import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.interval import Interval
from umlsl_edit.query.ast.ast import AtomNode, View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class FreeNode(AtomNode):
    """
    The FreeNode evaluates to true if the horizon if no car intersects the View.
    """
    def __init__(self):
        super().__init__("free")

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        if len(view.virtual_lanes) != 1 or view.horizon.length() <= 0:
            return False

        horizon = view.horizon

        # free is the derived formula  neg exists c: <re(c) or cl(c)>, so it is the reservations and
        # the claims that make a space occupied, not the physical extent of the cars: a car's safety
        # envelope reaches beyond its body, and that space is not free.
        #
        # Two spaces that merely touch do not overlap. A reservation ending exactly where this
        # observed space begins therefore leaves it free, which is what makes "re(c) hchop free"
        # satisfiable at the endpoint of c's reservation.
        for occupancy in (view.get_reserved_segments(), view.get_claimed_segments()):
            for segment_intervals in occupancy.values():
                for segment, interval in segment_intervals.items():
                    overlap = horizon.intersection(interval)
                    if overlap is not None and overlap.length() > 0:
                        return False

        return True
