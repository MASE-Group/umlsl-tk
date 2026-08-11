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
        # We shrink the horizon a little bit to avoid conflicts with "{reserve, claim} hchop free" (since on the boundary,
        # they won't evaluate true). Therefore, hchop would not be able to detect the collision directly (when evaluated
        # specifically at the boundaries) but only when iterating through the horizon with a certain step size - lowering
        # the precision to detect such instances.
        horizon_reduction = 0.001

        smaller_start = horizon.start + horizon_reduction
        smaller_end = max(smaller_start, horizon.end - horizon_reduction)
        smaller_horizon = Interval(smaller_start, smaller_end)

        for intersecting_car_uids, segment_intervals in view.get_visible_cars().items():
            for segment, interval in segment_intervals.items():
                if smaller_horizon.intersects(interval):
                    return False

        return True
