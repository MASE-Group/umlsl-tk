from itertools import product
from typing import TYPE_CHECKING

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.environment.car_environment import CarEnvironment
from umlsl_edit.model.environment.helpers.segment_intervals_helper import (
    compute_physical_segment_intervals,
    compute_segments_safety_envelope,
)
from umlsl_edit.model.environment.helpers.segment_topology_helper import (
    compute_parallel_lane_segments,
    compute_path_through_crossing,
)
from umlsl_edit.model.environment.helpers.turn_intent_helper import (
    find_turn_intent_segment,
)
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import (
    LaneSegment,
)
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import (
    SegmentInterval,
)
from umlsl_edit.model.traffic_value_objects.segments.virtual_lane import (
    VirtualLane,
)
from umlsl_edit.model.traffic_value_objects.turn_intent import (
    TurnDirection,
    TurnIntent,
)

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import CarParams


class EnvironmentCreation:
    """"
    Creates the car_environment.
    """

    def __init__(self, ts: TrafficSnapshotReader, car_params: "CarParams", settings: SettingsModel):
        self.ts = ts
        self.car_params = car_params
        self.settings = settings

        self.lane = self.car_params.lane
        self.road = self.ts.get_road_by_uid(self.lane.road_uid)

        self.pos_on_lane = self.car_params.position_on_lane  # rear of the car
        start_segment = self.ts.get_segment_from_lane_position(self.car_params.lane, self.pos_on_lane)
        if start_segment is None or not isinstance(start_segment, LaneSegment):
            raise ValueError("Car must start on a lane segment.")
        self.start_segment = start_segment

        self.car_direction = self._compute_car_direction()
        self.pos_on_segment = self._compute_pos_on_segment()

        if car_params.next_turn is None:
            # if the turn_intent is not specified, it means the car drives straight
            self.specified_turn_intent = TurnIntent(TurnDirection.STRAIGHT, car_params.lane)
            self.specified_turn_direction = TurnDirection.STRAIGHT
        else:
            self.specified_turn_intent = car_params.next_turn
            self.specified_turn_direction = car_params.next_turn.direction

    def _compute_car_direction(self) -> Direction:
        speed = self.car_params.speed

        car_direction: Direction
        if self.road.orientation == RoadOrientation.HORIZONTAL:
            car_direction = Direction.LEFT if (speed < 0) else Direction.RIGHT
        else:
            car_direction = Direction.DOWN if (speed < 0) else Direction.UP
        if not self.lane.is_forward():
            car_direction = car_direction.opposite
        return car_direction

    def _compute_pos_on_segment(self) -> float:
        segment_start_pos = self.start_segment.get_position(self.ts)[self.road.orientation.value]
        match self.car_direction:
            case Direction.RIGHT:
                return self.pos_on_lane - segment_start_pos
            case Direction.LEFT:
                return self.start_segment.get_size_in_direction(self.ts) - (self.pos_on_lane - segment_start_pos)
            case Direction.UP:
                return self.start_segment.get_size_in_direction(self.ts) - (segment_start_pos - self.pos_on_lane)
            case Direction.DOWN:
                return segment_start_pos - self.pos_on_lane

    @staticmethod
    def validate_environment(ts: TrafficSnapshotReader, pos_on_lane: float, lane: Lane) -> bool:
        # ensure the car is placed on a lane segment (not a crossing)
        return isinstance(ts.get_segment_from_lane_position(lane, pos_on_lane), LaneSegment)

    def build(self) -> CarEnvironment:
        """
        Creates the CarEnvironment.

        Raises:
            ValueError: If the car's specified turn intent leads to an invalid path.
            ValueError: If the computed path does not end on a LaneSegment.

        Returns:
            CarEnvironment: The computed car environment instance
        """
        turn_segment: LaneSegment = find_turn_intent_segment(self.ts, self.start_segment, self.specified_turn_intent,
                                                             self.car_direction)

        # We first compute the unbounded path segments (we suppose the car has an infinite horizon).
        # We then compute the horizon and cut off the unbounded path segments.
        unbounded_path_segments: list[Segment] | None = compute_path_through_crossing(self.ts, self.start_segment,
                                                                                      turn_segment)
        if unbounded_path_segments is None:
            raise ValueError("Car specified a turn intent with invalid path.")

        braking_dist: float = self.settings.braking_distance()
        pos_segment_behind: float = max(0.0, self.pos_on_segment - braking_dist)

        path_segments_size = braking_dist + self.pos_on_segment - pos_segment_behind
        path_segment_intervals = compute_segments_safety_envelope(
            self.ts,
            unbounded_path_segments,
            pos_segment_behind,
            path_segments_size,
            self.car_params.length
        )
        horizon_of_path = self._compute_horizon(pos_segment_behind, path_segment_intervals)
        physical_segment_intervals: list[SegmentInterval] = compute_physical_segment_intervals(
            self.ts,
            unbounded_path_segments,
            self.pos_on_segment,
            self.car_params.get_braking_dist(self.settings.braking_acceleration)
        )

        # We update the turn_segment if the next crossing is not in the view of the car.
        # This has the advantage we can safely rely on the turn_segment to compute the multi-view
        # without having to check the visibility of the turn segment again.
        turn_direction = self.specified_turn_direction
        if turn_segment not in unbounded_path_segments:
            end_lane: Segment = unbounded_path_segments[-1]
            if not isinstance(end_lane, LaneSegment):
                raise ValueError("Path must end on a lane segment.")
            turn_segment = end_lane
            turn_direction = TurnDirection.STRAIGHT

        parallel_virtual_lanes, path_virtual_lane, horizon = self.compute_parallel_virtual_lanes_intervals(
            unbounded_path_segments,
            path_segment_intervals,
            horizon_of_path,
            turn_segment,
            turn_direction
        )

        reserved_segment_intervals: list[SegmentInterval] = compute_segments_safety_envelope(
            self.ts,
            unbounded_path_segments,
            self.pos_on_segment,
            self.car_params.get_braking_dist(self.settings.braking_acceleration),
            self.car_params.length
        )
        claimed_segment_intervals: list[SegmentInterval] = self._compute_claimed_envelope(
            reserved_segment_intervals,
            self.car_params.transition,
        )

        car_environment = CarEnvironment(
            self.car_direction,
            turn_direction,
            unbounded_path_segments,
            horizon,
            parallel_virtual_lanes,
            path_virtual_lane,
            path_segment_intervals,
            physical_segment_intervals,
            reserved_segment_intervals,
            claimed_segment_intervals
        )
        # car_environment.print_debug(self.ts, self.car_params.name)
        return car_environment

    def _compute_horizon(self, backward_length: float, segment_intervals: list[SegmentInterval]) -> Interval:
        forward_length: float = backward_length

        for segment_interval in segment_intervals:
            forward_length += segment_interval.interval.length()

        return Interval(backward_length, forward_length)

    def compute_parallel_virtual_lanes_intervals(
            self,
            unbounded_path: list[Segment],
            path_segment_intervals: list[SegmentInterval],
            horizon_of_path: Interval,
            turn_segment: LaneSegment,
            turn_direction: TurnDirection
    ) -> tuple[list[list[VirtualLane]], VirtualLane, Interval]:
        """
        Computes the parallel virtual lanes with each segment being equipped with an interval information.

        Args:
            unbounded_path: the unbounded path pursuit by the car
            path_segment_intervals: the segment intervals of the pursuit path by the car
            horizon_of_path: the horizon of the car in its pursuit path
            turn_segment: the turn segment of the car
            turn_direction: the turn direction of the car
        Returns: parallel_virtual_lanes, path_virtual_lane, horizon
            parallel_virtual_lanes: the parallel virtual lanes
            path_virtual_lane: the virtual lane of the path of the car
            horizon: the horizon of the parallel virtual lanes
        """

        # We first compute the (unbounded) parallel virtual lanes segments (each segment is not yet equipped with its
        # interval information).
        parallel_segments = self._compute_parallel_virtual_lanes(turn_segment, turn_direction)

        # We now compute the intervals of the parallel virtual lanes.
        # Naively, one could just compute the intervals of each parallel-virtual-lane segment inside the horizon of ego.
        # However, on turns at crossings, this would result in ego seeing varying distances *behind* the crossing,
        # since the *length behind the crossing* of the path of ego [lane1, cs, cs, cs, lane2] will be less than
        # in the virtual lane [other_lane, cs, lane2]. That means ego will see further on lane2 in the second virtual lane
        # than on the first virtual lane.
        # Most importantly, using ego's horizon may result in ego not seeing over the full crossing on some parallel
        # virtual lane.
        # To solve this problem, we only measure the distance the car travels on lane segments. Concretely, we compute
        # the distance on lane segments in ego's path. We then compute the parallel virtual lanes and take the maximum
        # horizon, so the car will see the full crossing in all virtual lanes.
        lane_dist_in_path: float = 0.0
        for path_segment_interval in path_segment_intervals:
            if path_segment_interval.segment.is_lane_segment:
                lane_dist_in_path += path_segment_interval.interval.length()

        parallel_virtual_lanes_intervals: list[list[VirtualLane]] = []
        max_horizon: Interval = horizon_of_path
        for parallel_segment in parallel_segments:
            virtual_lanes: list[VirtualLane] = []

            for segment_list in parallel_segment:
                virtual_lane, horizon = self._segments_to_virtual_lane(segment_list, horizon_of_path, lane_dist_in_path)
                virtual_lanes.append(virtual_lane)
                if max_horizon.length() <= horizon.length():
                    max_horizon = horizon

            parallel_virtual_lanes_intervals.append(virtual_lanes)

        path_virtual_lane, _ = self._segments_to_virtual_lane(unbounded_path, horizon_of_path, lane_dist_in_path)
        return parallel_virtual_lanes_intervals, path_virtual_lane, max_horizon

    def _segments_to_virtual_lane(self, segments: list[Segment], horizon_on_lane: Interval,
                                  max_dist_on_lanes: float) -> tuple[VirtualLane, Interval]:
        current_pos = horizon_on_lane.start
        dist_on_lanes: float = 0.0

        segment_intervals: list[SegmentInterval] = []
        for i, segment in enumerate(segments):
            # in the first iteration, we need to add the remaining length of the segment to the current position
            segment_size = segment.get_size_in_direction(self.ts)
            segment_length = (segment_size - current_pos) if i == 0 else segment_size

            if segment.is_lane_segment:
                new_dist_on_lanes = dist_on_lanes + segment_length
                if new_dist_on_lanes > max_dist_on_lanes:
                    remaining_size = max(0.0, max_dist_on_lanes - dist_on_lanes)
                    segment_intervals.append(
                        SegmentInterval(segment, Interval(current_pos, current_pos + remaining_size))
                    )
                    break
                else:
                    segment_intervals.append(
                        SegmentInterval(segment, Interval(current_pos, current_pos + segment_length)))
                    dist_on_lanes = new_dist_on_lanes
            else:
                segment_intervals.append(SegmentInterval(segment, Interval(current_pos, current_pos + segment_length)))

            current_pos += segment_length

        horizon_of_virtual_lane: Interval = self._compute_horizon(horizon_on_lane.start, segment_intervals)

        return VirtualLane(segment_intervals), horizon_of_virtual_lane

    def _compute_parallel_virtual_lanes(
            self, turn_segment: LaneSegment,
            turn_direction: TurnDirection) -> list[list[list[Segment]]]:
        src_segments: list[LaneSegment] = compute_parallel_lane_segments(self.ts, self.start_segment, 1)
        start_road_orientation: RoadOrientation = self.ts.get_road_by_uid(self.start_segment.lane.road_uid).orientation

        if start_road_orientation == RoadOrientation.VERTICAL and turn_direction == TurnDirection.LEFT:
            src_segments.reverse()

        target_segments: list[LaneSegment] = compute_parallel_lane_segments(self.ts, turn_segment, 1)

        order_lanes: list[list[list[Segment]]] = []
        for src_seg in src_segments:
            paths = []
            for target_segment in target_segments:
                path: list[Segment] | None = compute_path_through_crossing(self.ts, src_seg, target_segment)
                if path is not None:
                    paths.append(path)
                else:
                    path = compute_path_through_crossing(self.ts, target_segment, src_seg)
                    if path is not None:
                        path.reverse()
                        paths.append(path)

            if len(paths) > 0:
                order_lanes.append(paths)

        parallel_lanes: list[list[list[Segment]]] = [list(p) for p in product(*order_lanes)]

        return parallel_lanes

    def _compute_claimed_envelope(self, reserved_segment_intervals: list[SegmentInterval], transition: float) -> list[
        SegmentInterval]:
        if transition == 0 or len(reserved_segment_intervals) != 1:
            return []

        segment_interval: SegmentInterval = reserved_segment_intervals[0]
        if not isinstance(segment_interval.segment, LaneSegment):
            raise ValueError("Car cannot transition on a non-lane segment.")

        lane_segment: LaneSegment = segment_interval.segment

        parallel_segments = compute_parallel_lane_segments(self.ts, lane_segment)
        current_index = parallel_segments.index(lane_segment)

        road = self.ts.get_road_by_uid(segment_interval.segment.lane.road_uid)
        delta = 1 if transition > 0 else -1
        if road.orientation == RoadOrientation.HORIZONTAL:
            delta = -delta

        # 1 means up/right, -1 means down/left
        # The segments are sorted by lane index which matches this mapping.
        claimed_segment_index = current_index + delta
        claimed_segment = parallel_segments[claimed_segment_index]

        return [SegmentInterval(claimed_segment, segment_interval.interval)]
