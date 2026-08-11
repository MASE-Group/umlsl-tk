import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.query.ast.ast import View, AtomNode
from umlsl_edit.query.ast.car_resolve import CarResolve

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class ReserveNode(AtomNode):
    """
    A ReserveNode is a unary node that evaluates to true if the horizon is fully covered by the reserved segments of the
    given car.
    """
    def __init__(self, car_resolve: CarResolve):
        super().__init__(f"re\\left({car_resolve.name}\\right)")
        self._car_resolve = car_resolve

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        if len(view.virtual_lanes) != 1 or view.horizon.length() <= 0:
            return False

        # the car to evaluate the reserve node on
        eval_car = self._car_resolve.resolve(variable_car_map)
        reserved_segments = view.get_reserved_segments().get(eval_car.uid)
        if reserved_segments is None:
            return False

        car_reserved_segments: list[Segment] = list(reserved_segments.keys())
        single_lane = view.virtual_lanes[0]
        reserved_intervals: list[Interval] = []
        for segment_interval in single_lane.segment_intervals:
            segment = segment_interval.segment
            # we have to ensure every segment of the lane is contained in a reserved segment of the car
            if segment_interval.segment not in car_reserved_segments:
                return False

            interval = reserved_segments.get(segment)
            if interval is None:
                return False

            reserved_intervals.append(interval)

        # check if the horizon is fully contained in the reserved segments of the car
        return view.horizon.subset_of(Interval.union(reserved_intervals))
