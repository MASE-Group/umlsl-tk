import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.interval import Interval
from umlsl_edit.query.ast.ast import AtomNode, View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class CrossingSegmentNode(AtomNode):
    """
    The CrossingSegmentNode is a unary node that evaluates to true if the horizon is fully covered by crossing segments.
    """
    def __init__(self):
        super().__init__("cs")

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        if len(view.virtual_lanes) != 1 or view.horizon.length() <= 0:
            return False

        # a lane may end before the horizon does, so it is not enough that no lane segment is in view
        single_lane = view.virtual_lanes[0]
        crossing_intervals = [segment_interval.interval for segment_interval in single_lane.segment_intervals
                              if not segment_interval.segment.is_lane_segment]

        return view.horizon.subset_of(Interval.union(crossing_intervals))
