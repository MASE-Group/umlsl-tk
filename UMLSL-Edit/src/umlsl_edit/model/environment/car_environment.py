from dataclasses import dataclass
from typing import TYPE_CHECKING

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import SegmentInterval
from umlsl_edit.model.traffic_value_objects.segments.virtual_lane import VirtualLane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import Car


@dataclass(frozen=True)
class CarEnvironment:
    """
    The car environment holds all information about how a car perceives its environment.

    Attributes:
        car_direction: the driving direction of the car
        turn_direction: the turn direction of the car
        path: the pursuit path of
        horizon: the horizon (relative to the segment the car is standing on)
        parallel_virtual_lanes: the list of parallel virtual lanes according to UMLSL logic
        path_virtual_lane: the virtual lane corresponding to the car's path
        path_segment_intervals: the segment intervals of the car's path
        physical_segment_intervals: the segment intervals of the car's physically occupied segments
        reserved: the list of reserved segments (each interval information is measured relative to the segment's position)
        claimed: the list of claimed segments (each interval information is measured relative to the segment's position)
    """

    car_direction: Direction
    turn_direction: TurnDirection

    path: list[Segment]
    horizon: Interval
    parallel_virtual_lanes: list[list[VirtualLane]]
    path_virtual_lane: VirtualLane

    path_segment_intervals: list[SegmentInterval]
    physical_segment_intervals: list[SegmentInterval]

    reserved: list[SegmentInterval]
    claimed: list[SegmentInterval]

    def print_debug(self, ts: TrafficSnapshotReader, car_name: str):
        print(f"--- debug --- env of {car_name}")
        print("path is ", list(map(lambda seg: ts.get_segment_info(seg.uid), self.path)))

        def format_seg_intervals(segment_intervals: list[SegmentInterval]) -> str:
            return " ".join(
                map(lambda seg: ts.get_segment_info(seg.segment.uid) + " " + str(seg.interval), segment_intervals))

        print("horizon is ", self.horizon)
        print("path seg-intervals is ", format_seg_intervals(self.path_segment_intervals))
        print("physical segment intervals are ", format_seg_intervals(self.physical_segment_intervals))
        print("reserved segment intervals are ", format_seg_intervals(self.reserved))
        print("claimed segment intervals are ", format_seg_intervals(self.claimed))

        for parallel_virtual_lane in self.parallel_virtual_lanes:
            print("parallel virtual lane:")
            for virtual_lane in parallel_virtual_lane:
                print(" > virtual lane is ", format_seg_intervals(virtual_lane.segment_intervals))

    def translate_interval_coordinates(self, virtual_lanes: list[VirtualLane], horizon: Interval,
                                       to_translate: list[SegmentInterval], translate_car: 'Car',
                                       ts: TrafficSnapshotReader) -> dict[Segment, Interval]:
        """"
        Translates the segment of the given interval into the coordinates of the "self" car on the given virtual lanes
        (that is an element of ego's parallel virtual lanes).
        """

        car_dir: Direction = translate_car.environment.car_direction
        swap_alignment = self._swap_alignment(car_dir)

        # The logic follows three main steps:
        # 1. Directional Alignment: If the target car is facing the opposite direction
        #    of the ego car, we flip the start/end points of the intervals (remember that the interval information
        #    is relative to the segment's position - so we flip that).
        # 2. Lane Mapping: We look up which virtual lane each segment belongs to and
        #    organize the intervals accordingly.
        # 3. Absolute Projection: Finally, we convert these segment-relative distances
        #    into a continuous coordinate system along the ego's path (that means we convert the relative
        #    interval information into absolute intervals that increase along the path).

        # 1. Align intervals
        aligned_to_translate: list[SegmentInterval] = []
        if swap_alignment:
            for translate_segment_interval in to_translate:
                # swap the start and end of the interval (measure from the opposite site of the segment)
                segment = translate_segment_interval.segment
                segment_length = segment.get_size_in_direction(ts)
                interval = translate_segment_interval.interval

                new_start = segment_length - interval.end
                new_end = segment_length - interval.start

                aligned_interval = Interval(new_start, new_end)
                aligned_to_translate.append(SegmentInterval(segment, aligned_interval))
        else:
            aligned_to_translate = to_translate

        # 2. Map intervals to virtual lanes
        segments_to_virtual_lane: dict[Segment, int] = {}
        for virtual_lane_index in virtual_lanes:
            for segment_interval in virtual_lane_index.segment_intervals:
                lane_index = virtual_lanes.index(virtual_lane_index)
                segments_to_virtual_lane[segment_interval.segment] = lane_index

        # 3. Translate interals to absolute coordinates
        lane_to_segment_intervals: dict[int, dict[Segment, Interval]] = {}
        for translate_segment_interval in aligned_to_translate:
            lane_index = segments_to_virtual_lane.get(translate_segment_interval.segment)
            if lane_index is not None:
                if lane_to_segment_intervals.get(lane_index) is None:
                    lane_to_segment_intervals[lane_index] = {}

                lane_to_segment_intervals[lane_index][
                    translate_segment_interval.segment] = translate_segment_interval.interval

        translated_segment_intervals = self._translate_to_lane_abs_pos(virtual_lanes, lane_to_segment_intervals, horizon, ts)

        return translated_segment_intervals

    def _translate_to_lane_abs_pos(
            self, virtual_lanes: list[VirtualLane], lane_to_segment_intervals: dict[int, dict[Segment, Interval]],
            horizon: Interval, ts: TrafficSnapshotReader) -> dict[Segment, Interval]:
        translated_segment_intervals: dict[Segment, Interval] = {}
        for lane_index, virtual_lane in enumerate(virtual_lanes):
            segment_intervals_on_lane: dict[Segment, Interval] = lane_to_segment_intervals.get(lane_index)
            if segment_intervals_on_lane is None:
                continue

            offset = 0
            for lane_segment_interval in virtual_lane.segment_intervals:
                lane_segment = lane_segment_interval.segment

                interval = segment_intervals_on_lane.get(lane_segment)
                if interval is not None:
                    interval_on_lane = Interval(interval.start + offset, interval.end + offset)
                    if interval_on_lane.intersects(horizon):
                        translated_segment_intervals[lane_segment] = interval_on_lane

                offset += lane_segment.get_size_in_direction(ts)
        return translated_segment_intervals

    def _swap_alignment(self, car_dir: Direction) -> bool:
        self_dir: Direction = self.car_direction
        self_turn_dir: TurnDirection = self.turn_direction

        if car_dir == self_dir.opposite:
            return True

        if self_turn_dir != TurnDirection.STRAIGHT and car_dir != self_dir:
            match self_dir:
                case Direction.RIGHT:
                    return (self_turn_dir == TurnDirection.LEFT and car_dir == Direction.DOWN
                            or self_turn_dir == TurnDirection.RIGHT and car_dir == Direction.UP)
                case Direction.LEFT:
                    return (self_turn_dir == TurnDirection.LEFT and car_dir == Direction.UP
                            or self_turn_dir == TurnDirection.RIGHT and car_dir == Direction.DOWN)
                case Direction.UP:
                    return (self_turn_dir == TurnDirection.LEFT and car_dir == Direction.RIGHT
                            or self_turn_dir == TurnDirection.RIGHT and car_dir == Direction.LEFT)
                case Direction.DOWN:
                    return (self_turn_dir == TurnDirection.LEFT and car_dir == Direction.LEFT
                            or self_turn_dir == TurnDirection.RIGHT and car_dir == Direction.RIGHT)

        return False
