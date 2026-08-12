import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.query.ast.ast import View, AtomNode
from umlsl_edit.query.ast.car_resolve import CarResolve

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class ClaimNode(AtomNode):
    """
    The ClaimNode is a unary node used to check for the existence of a claimed segments of the specified car in
    ego's view.
    """

    def __init__(self, car_resolve: CarResolve):
        super().__init__(f"cl\\left({car_resolve.name}\\right)")
        self._car_resolve = car_resolve

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        if len(view.virtual_lanes) != 1 or view.horizon.length() <= 0:
            return False

        # cl(C) holds iff the observed space lies entirely inside the space claimed by C, mirroring
        # re(C). Claims are tracked per segment, so every segment the observed space runs over has
        # to be claimed by C, and the observed space has to be covered by those claimed intervals.
        car_eval = self._car_resolve.resolve(variable_car_map)
        claimed_segments = view.get_claimed_segments().get(car_eval.uid)
        if not claimed_segments:
            return False

        single_lane = view.virtual_lanes[0]
        claimed_intervals: list[Interval] = []
        for segment_interval in single_lane.segment_intervals:
            segment: Segment = segment_interval.segment
            interval = claimed_segments.get(segment)
            if interval is None:
                return False

            claimed_intervals.append(interval)

        return view.horizon.subset_of(Interval.union(claimed_intervals))
