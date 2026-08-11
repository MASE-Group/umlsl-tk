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

        single_lane = view.virtual_lanes[0]
        segments_on_lane = list(map(lambda si: si.segment, single_lane.segment_intervals))

        car_eval = self._car_resolve.resolve(variable_car_map)
        claimed_segment_intervals: dict[Segment, Interval] = view.get_claimed_segments().get(car_eval.uid, {})
        claimed_crossing_segments = map(
            lambda seg_interval: seg_interval.segment,
            filter(lambda segment: not segment.is_lane_segment, claimed_segment_intervals.keys())
        )

        # claim evaluates true if all segments (in the horizon) are crossing segments reserved by the (eval) car
        if all(map(lambda claimed: claimed in claimed_crossing_segments, segments_on_lane)):
            return True

        # otherwise, we need to check whether the horizon is fully contained in the segment of the (eval) car
        if len(segments_on_lane) != 1:
            return False

        single_segment = segments_on_lane[0]

        for physically_occupied_segment, physically_occupied_interval in view.get_visible_cars().get(car_eval.uid,
                                                                                                     {}).items():
            if physically_occupied_segment.uid == single_segment.uid \
                    and view.horizon.subset_of([physically_occupied_interval]):
                return True

        return False
