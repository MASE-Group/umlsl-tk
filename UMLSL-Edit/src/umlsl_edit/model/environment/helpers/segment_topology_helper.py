from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import LaneSegment
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment


def compute_path_through_crossing(
        ts: TrafficSnapshotReader,
        start: LaneSegment,
        end: LaneSegment
) -> list[Segment] | None:
    """"
    Computes the path from start to end through a crossing segment using a column-like search algorithm.

    Args:
        ts: the traffic snapshot
        start: the starting segment
        end: the ending segment
    Returns:
        the list of segments through the crossing
    """
    if start == end:
        return [start]

    relative_start_to_end = _compute_relative_direction(ts, start, end)
    relative_end_to_start = _compute_relative_direction(ts, end, start)

    # With this relative information, we can iterate in the opposite direction of "relative_start_to_end" (so we
    # iteratively enter the crossing). We call this segment the "search node". We then iterate from that search node
    # in the direction of "relative_end_to_start" to reach the final segment while always collecting the path data.
    search_node = ts.get_outgoing_adjacent_segment(start.uid, relative_start_to_end.opposite)
    forward_path: list[Segment] = [start, search_node]

    while search_node is not None:
        next_segment = ts.get_outgoing_adjacent_segment(search_node.uid, relative_end_to_start)

        path: list[Segment] = forward_path + [next_segment]
        while next_segment is not None:
            if next_segment == end:
                return path
            elif next_segment.is_lane_segment:
                break

            next_segment = ts.get_outgoing_adjacent_segment(next_segment.uid, relative_end_to_start)
            path.append(next_segment)

        search_node = ts.get_outgoing_adjacent_segment(search_node.uid, relative_start_to_end.opposite)
        forward_path.append(search_node)

    return None


def _compute_relative_direction(ts: TrafficSnapshotReader, lane1: LaneSegment, lane2: LaneSegment) -> Direction:
    pos1 = lane1.get_position(ts)
    pos2 = lane2.get_position(ts)

    orientation_1 = ts.get_road_by_uid(lane1.lane.road_uid).orientation
    if orientation_1 == RoadOrientation.VERTICAL:
        return Direction.DOWN if pos1[1] < pos2[1] else Direction.UP
    else:
        # horizontal
        return Direction.LEFT if pos1[0] < pos2[0] else Direction.RIGHT


def compute_parallel_lane_segments(ts: TrafficSnapshotReader, segment: LaneSegment, dist: int = -1) -> list[
    LaneSegment]:
    """"
    Computes the segments parallel to the given lane segment whose distance is <= the given distance away (set to -1
    to ignore).
    Parallel means that the segments are parallel to the driving direction of the lane segment.
    The given segment is included in the result, which is sorted by each segment's index.

    Args:
        ts: the traffic snapshot
        segment: the segment to compute the parallel segments for
        dist: how many lanes to expand in both directions, -1 to consider all parallel lane segments
    Returns:
        the list of parallel lane segments
    """

    assert segment.is_lane_segment
    lane_segment: LaneSegment = segment
    road = ts.get_road_by_uid(lane_segment.lane.road_uid)

    directions = [Direction.LEFT, Direction.RIGHT] if road.orientation == RoadOrientation.VERTICAL \
        else [Direction.UP, Direction.DOWN]

    segments: list[LaneSegment] = [segment]
    for direction in directions:
        next_segment = ts.get_adjacent_segment(segment.uid, direction)
        advancement = 0
        while next_segment is not None and (advancement < dist or dist == -1):
            # if we start on a lane segment and move orthogonal to its driving direction, we cannot reach a crossing
            # segment
            assert isinstance(next_segment, LaneSegment)
            segments.append(next_segment)
            next_segment = ts.get_adjacent_segment(next_segment.uid, direction)
            advancement += 1

    segments.sort(key=lambda seg: seg.lane.lane_index)
    return segments
