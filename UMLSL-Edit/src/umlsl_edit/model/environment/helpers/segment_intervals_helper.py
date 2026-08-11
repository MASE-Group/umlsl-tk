from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import SegmentInterval

"""
This file includes helper functions for equipping each segment with its interval information for a specified path (list
of segments).
"""


def compute_physical_segment_intervals(
        ts: TrafficSnapshotReader,
        path: list[Segment],
        pos_on_segment: float,
        car_size: float
) -> list[SegmentInterval]:
    """"
    This algorithm computes the real space (physical segments) a car occupies on a path and equips them with
    its interval information. That means segments that are outside the occupied space of the car are not included.

    Note that the interval of each "segment" is measured with respect to the start position of that "segment".
    As an example, consider a realistic path (lane1, cs1, cs2, lane2). The computed result may look like
    ([lane1, (pos_on_segment, size_lane1)], [cs2, (0, size_cs2)], [cs3, (0, end_pos_on_segment)]).

    It is similar to the "Algorithm 2" (seg_V) method in the paper, except we do not filter whether the physical
    segments are inside a view (we collect all physical segments).

    Args:
        ts: the traffic snapshot
        path: the path to compute the segment intervals (list of segments)
        pos_on_segment: the position of the car on the segment (measured relative to that segment, i.e., 0 <= pos_on_segment <= segment_size)
        car_size: the size of the car
    """
    interval_start_offset = pos_on_segment

    result = []
    next_size = car_size

    i = 0
    while next_size > 0:
        current_size = next_size

        if i >= len(path):
            return result

        seg_i = path[i]

        b_i: float
        if seg_i.is_lane_segment:
            b_i = min(interval_start_offset + current_size, seg_i.get_size_in_direction(ts))
        else:
            b_i = seg_i.get_size_in_direction(ts)

        interval = Interval(interval_start_offset, b_i)
        next_size = current_size - interval.length()

        interval_start_offset = 0

        result.append(SegmentInterval(seg_i, interval))
        i += 1

    return result


def compute_segments_safety_envelope(
        ts: TrafficSnapshotReader,
        path: list[Segment],
        pos_on_segment: float,
        car_size: float,
        safety_envelope: float
) -> list[SegmentInterval]:
    """"
    This algorithm computes the real space (physical segments) a car occupies on a path, equips them with
    its interval information, and includes a safety envelope (that equals the car_size parameter), so the car does not
    stop inside a crossing. If the car does not stop on a crossing, the safety envelope is not included.

    Note that the interval of each "segment" is measured with respect to the start position of that "segment".
    As an example, consider a realistic path (lane1, cs1, cs2, lane2) with the car's physical size stopping on cs2.
    The computed result may look like
    ([lane1, (pos_on_segment, size_lane1)], [cs2, (0, size_cs2)], [cs3, (0, size_cs2)], [lane2, (0, car_size)]).

    Args:
        ts: the traffic snapshot
        path: the path to compute the segment intervals (list of segments)
        pos_on_segment: the position of the car on the segment (measured relative to that segment, i.e., 0 <= pos_on_segment <= segment_size)
        car_size: the size of the horizon (measured relative to the car's position)
        safety_envelope: the length of the safety envelope
    Returns:
        the list of segment intervals, each interval is measured relatively to its segment
    """
    interval_start_offset = pos_on_segment

    result = []
    size = car_size

    i = 0
    while size > 0 and i < len(path):
        seg_i = path[i]
        seg_size = seg_i.get_size_in_direction(ts)

        b_i: float
        if seg_i.is_lane_segment:
            b_i = min(interval_start_offset + size, seg_size)
            length = b_i - interval_start_offset
            size -= length
        else:
            b_i = seg_size
            length = b_i - interval_start_offset
            # if the car ends in a crossing, we make sure the segment_intervals are expanded until after the crossing
            size = max(size - length, safety_envelope)

        interval = Interval(interval_start_offset, b_i)

        interval_start_offset = 0

        result.append(SegmentInterval(seg_i, interval))
        i += 1

    return result
