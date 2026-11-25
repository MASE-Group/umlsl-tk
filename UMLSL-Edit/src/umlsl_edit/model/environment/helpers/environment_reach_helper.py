"""
How far a car's environment reaches in world coordinates.

The world extent (``WorldExtentMixin``) is measured with these functions: a lane with no crossing in some direction
ends where the farthest environment on the canvas ends, plus the view horizon. The conversion to world coordinates is
the one the canvas draws the environment with, so the extent fits exactly what the editor shows.
"""
from typing import TYPE_CHECKING

from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import LaneSegment
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import (
    SegmentInterval,
    ViewSegmentIntervall,
)

if TYPE_CHECKING:
    from umlsl_edit.model.entities.car import Car


def to_view_segment_intervals(segment_intervals: list[SegmentInterval]) -> list[ViewSegmentIntervall]:
    """
    The segment intervals of a virtual lane, each aligned to the offset its virtual lane has reached.

    The intervals of a virtual lane are measured along the whole lane; this shifts each one back to its own segment.
    """
    view_intervals = []
    offset = 0.0
    path_segments = tuple(seg_interval.segment for seg_interval in segment_intervals)
    for seg_interval in segment_intervals:
        view_intervals.append(
            ViewSegmentIntervall(seg_interval.segment, seg_interval.interval, offset, path_segments)
        )
        offset = seg_interval.interval.end
    return view_intervals


def lane_interval_reach(
        ts: TrafficSnapshotReader,
        segment_interval: SegmentInterval,
        car: "Car",
        ignore_lane_direction: bool,
) -> tuple[int, float, float] | None:
    """
    Where a segment interval lies along its lane, in world coordinates.

    Returns:
        ``(axis, low, high)``, with axis 0 for x (a horizontal lane) and 1 for y (a vertical lane), or ``None`` for a
        crossing segment. Crossings need no measuring: they lie inside the roads that form them.
    """
    segment = segment_interval.segment
    if not isinstance(segment, LaneSegment):
        return None

    x_seg, y_seg = segment.get_position(ts)
    _, height_seg = segment.get_size(ts)
    interval = segment_interval.get_global_interval(ts, car, ignore_lane_direction)
    if ts.get_road_by_uid(segment.lane.road_uid).orientation == RoadOrientation.HORIZONTAL:
        return 0, x_seg + interval.start, x_seg + interval.end
    # the position of a vertical lane segment is its upper end
    low_end = y_seg - height_seg
    return 1, low_end + interval.start, low_end + interval.end


def environment_reach(ts: TrafficSnapshotReader, car: "Car") -> tuple[float, float]:
    """
    The largest distance from the origin, in x and in y, that the car's environment reaches along a lane.

    The environment is everything drawn for the car: its view (every parallel virtual lane), its physical space, its
    reservation and its claim. Distances across a road are left out, because the road itself covers them.
    """
    env = car.environment
    # The direction flags are the ones the canvas draws each kind of interval with.
    measured: list[tuple[SegmentInterval, bool]] = [(si, False) for si in env.physical_segment_intervals]
    measured += [(si, False) for si in env.reserved]
    measured += [(si, True) for si in env.claimed]
    for parallel_virtual_lane in env.parallel_virtual_lanes:
        for virtual_lane in parallel_virtual_lane:
            measured += [(si, True) for si in to_view_segment_intervals(virtual_lane.segment_intervals)]

    reach = [0.0, 0.0]
    for segment_interval, ignore_lane_direction in measured:
        lane_reach = lane_interval_reach(ts, segment_interval, car, ignore_lane_direction)
        if lane_reach is None:
            continue
        axis, low, high = lane_reach
        reach[axis] = max(reach[axis], abs(low), abs(high))
    return reach[0], reach[1]
