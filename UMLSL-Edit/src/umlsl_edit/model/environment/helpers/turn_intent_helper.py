from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import LaneSegment
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnIntent, TurnDirection


def find_turn_intent_segment(
        ts: TrafficSnapshotReader,
        start: LaneSegment,
        turn_intent: TurnIntent,
        car_direction: Direction
) -> LaneSegment:
    """"
    We need to find the target lane segment based on the turn intent and the car's current position.

    This algorithm works as follows: Since we know the target lane (this is not a segment - but a lane associated with
    a road), we collect all lane *segments* of that lane. Depending on the car's direction, we iterate through the
    lane segments and take the one corresponding to the turn.
    """
    start_coords = start.get_position(ts)
    # we need to find the target lane segment based on the turn intent

    # collect all segments of the target lane
    segments_of_target_lane: list[Segment] = []
    for segment in ts.all_segments():
        if isinstance(segment, LaneSegment):
            lane_segment: LaneSegment = segment
            if lane_segment.lane == turn_intent.target_lane:
                segments_of_target_lane.append(segment)

    turn_direction = turn_intent.direction
    start_road_direction = ts.get_road_by_uid(start.lane.road_uid).orientation

    # if there is no crossing on the road (-> 1 lane segment), we can terminate directly
    if len(segments_of_target_lane) == 1:
        assert turn_direction == TurnDirection.STRAIGHT
        return segments_of_target_lane[0]

    # for straight driving, we can iterate straight through the crossing and take the first lane segment
    if turn_direction == TurnDirection.STRAIGHT:
        next_segment = ts.get_adjacent_segment(start.uid, car_direction)
        if next_segment is None and start.is_lane_segment:
            return start
        while next_segment is not None:
            if isinstance(next_segment, LaneSegment):
                return next_segment
            next_segment = ts.get_adjacent_segment(next_segment.uid, car_direction)

    # the segment_position_index is used to consider only the relevant coordinate of the segments_of_target_lane list
    segment_position_index: int = 1 if start_road_direction == RoadOrientation.HORIZONTAL else 0
    segments_of_target_lane.sort(key=lambda x: x.get_position(ts)[segment_position_index])

    # we got a list of target lane segments (our candidates) and the information of the car
    # we need to find the one that is next to the car's position' depending on the turn direction
    if car_direction in {Direction.LEFT, Direction.UP}:
        if turn_direction == TurnDirection.LEFT:
            segments_of_target_lane.reverse()

            for segment in segments_of_target_lane:
                pos = segment.get_position(ts)[segment_position_index]
                start_pos = start_coords[segment_position_index]
                if isinstance(segment, LaneSegment) and pos < start_pos:
                    return segment
        else:
            for segment in segments_of_target_lane:
                pos = segment.get_position(ts)[segment_position_index]
                start_pos = start_coords[segment_position_index]
                if isinstance(segment, LaneSegment) and pos > start_pos:
                    return segment
    else:
        if turn_direction == TurnDirection.RIGHT:
            segments_of_target_lane.reverse()

            for segment in segments_of_target_lane:
                pos = segment.get_position(ts)[segment_position_index]
                start_pos = start_coords[segment_position_index]
                if isinstance(segment, LaneSegment) and pos < start_pos:
                    return segment
        else:
            for segment in segments_of_target_lane:
                pos = segment.get_position(ts)[segment_position_index]
                start_pos = start_coords[segment_position_index]
                if isinstance(segment, LaneSegment) and pos > start_pos:
                    return segment

    raise ValueError("Turn intent not found.")
