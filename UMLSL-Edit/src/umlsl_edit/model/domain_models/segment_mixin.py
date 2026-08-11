from typing import TYPE_CHECKING

from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.direction import Direction
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.segments.crossing_segment import CrossingSegment
from umlsl_edit.model.traffic_value_objects.segments.lane_segment import LaneSegment
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class SegmentMixin:
    def get_valid_turn_intent_lanes(
            self: "TrafficSnapshotModel",
            car_position: float,
            car_speed: float,
            car_lane: Lane,
            car_length: float,
            turn_direction: TurnDirection,
    ) -> list[Lane]:
        if car_speed < 0 or turn_direction not in [
            TurnDirection.LEFT,
            TurnDirection.RIGHT,
        ]:
            return []

        road_of_lane = self.get_road_by_uid(car_lane.road_uid)
        if road_of_lane is None:
            raise ValueError(f"Road with uid {car_lane.road_uid} not found.")

        if road_of_lane.orientation == RoadOrientation.HORIZONTAL:
            direction = Direction.RIGHT if car_lane.lane_index >= 0 else Direction.LEFT
        else:
            direction = Direction.UP if car_lane.lane_index >= 0 else Direction.DOWN

        segment = self.get_segment_from_lane_position(car_lane, car_position)

        if segment is None:
            return []

        lanes_to_turn_into: list[Lane] = []
        current_segment_uid = segment.uid
        adjacent_segment = self.get_adjacent_segment(current_segment_uid, direction)
        while isinstance(adjacent_segment, CrossingSegment):
            lane_to_turn_into = (
                adjacent_segment.horizontal_lane
                if road_of_lane.orientation == RoadOrientation.VERTICAL
                else adjacent_segment.vertical_lane
            )

            # go through all 4 casees
            if road_of_lane.orientation == RoadOrientation.HORIZONTAL:
                if turn_direction == TurnDirection.LEFT:
                    # lane indeces must be different
                    if (
                            car_lane.lane_index >= 0 and lane_to_turn_into.lane_index >= 0
                    ) or (car_lane.lane_index < 0 and lane_to_turn_into.lane_index < 0):
                        lanes_to_turn_into.append(lane_to_turn_into)
                elif turn_direction == TurnDirection.RIGHT:
                    # lane indeces must be the same
                    if (
                            car_lane.lane_index >= 0 and lane_to_turn_into.lane_index < 0
                    ) or (
                            car_lane.lane_index < 0 and lane_to_turn_into.lane_index >= 0
                    ):
                        lanes_to_turn_into.append(lane_to_turn_into)
            if road_of_lane.orientation == RoadOrientation.VERTICAL:
                if turn_direction == TurnDirection.LEFT:
                    # lane indeces must be different
                    if (
                            car_lane.lane_index >= 0 and lane_to_turn_into.lane_index < 0
                    ) or (
                            car_lane.lane_index < 0 and lane_to_turn_into.lane_index >= 0
                    ):
                        lanes_to_turn_into.append(lane_to_turn_into)
                elif turn_direction == TurnDirection.RIGHT:
                    # lane indeces must be the same
                    if (
                            car_lane.lane_index >= 0 and lane_to_turn_into.lane_index >= 0
                    ) or (car_lane.lane_index < 0 and lane_to_turn_into.lane_index < 0):
                        lanes_to_turn_into.append(lane_to_turn_into)
            adjacent_segment = self.get_adjacent_segment(
                adjacent_segment.uid, direction
            )

        return lanes_to_turn_into

    def get_adjacent_segment(
            self: "TrafficSnapshotModel", segment_uid: str, direction: Direction
    ) -> Segment | None:
        adjacent_uid = self._get_neighbor_in_direction(segment_uid, direction)
        if adjacent_uid is not None:
            return self._segments[adjacent_uid]
        return None

    def get_outgoing_adjacent_segment(
            self: "TrafficSnapshotModel", segment_uid: str, direction: Direction
    ) -> Segment | None:
        adjacent_uid = self._get_neighbor_in_direction_outgoing(segment_uid, direction)
        if adjacent_uid is not None:
            return self._segments[adjacent_uid]
        return None

    def get_segment_from_lane_position(
            self: "TrafficSnapshotModel", lane: Lane, position_on_lane: float
    ) -> Segment | None:
        segment_uids = self._segments_by_lane.get(lane)
        if segment_uids is None:
            return None

        segments: list[Segment] = []
        for seg_uid in segment_uids:
            segments.append(self._segments[seg_uid])

        road = self.get_road_by_uid(lane.road_uid)
        coord_index = 0 if road.orientation == RoadOrientation.HORIZONTAL else 1
        segments.sort(key=lambda s: s.get_position(self)[coord_index])
        if road.orientation == RoadOrientation.VERTICAL:
            segments.reverse()

        first_segment_on_road = segments[0]
        previous_segment: Segment | None = first_segment_on_road
        for segment in segments:
            seg_pos_on_lane = segment.get_position(self)[coord_index]
            if road.orientation == RoadOrientation.HORIZONTAL:
                if seg_pos_on_lane < position_on_lane:
                    previous_segment = segment
                else:
                    return previous_segment
            if road.orientation == RoadOrientation.VERTICAL:
                if seg_pos_on_lane > position_on_lane:
                    previous_segment = segment
                else:
                    return previous_segment

        return previous_segment

    def all_segments(self: "TrafficSnapshotModel") -> list[Segment]:
        segments = []
        for segment in self._segments.values():
            segments.append(segment)

        return segments

    def _get_neighbor_in_direction(
            self: "TrafficSnapshotModel", segment_uid: str, direction: Direction
    ) -> str | None:
        """Get the neighboring segment UID in a given direction from the graph."""
        for _, neighbor, data in self._graph.out_edges(segment_uid, data=True):
            if data.get("direction") == direction:
                return neighbor
        for neighbor, _, data in self._graph.in_edges(segment_uid, data=True):
            if data.get("direction") == direction.opposite:
                return neighbor
        return None

    def _get_neighbor_in_direction_outgoing(
            self: "TrafficSnapshotModel", segment_uid: str, direction: Direction
    ) -> str | None:
        """Get the neighboring segment UID in a given direction from the graph."""
        for _, neighbor, data in self._graph.out_edges(segment_uid, data=True):
            if data.get("direction") == direction:
                return neighbor
        return None

    def _get_segment_by_uid(self: "TrafficSnapshotModel", segment_uid: str) -> Segment:
        segment = self._segments.get(segment_uid)
        if segment is None:
            raise ValueError(f"Segment with uid {segment_uid} not found.")
        return segment

    def _recalculate_static_segments(self: "TrafficSnapshotModel") -> None:
        """
        Recalculate all static segments and their connections based on current roads.

        This builds:
        - CrossingSegments where horizontal and vertical lanes intersect
        - LaneSegments between crossings and at the boundaries (connecting to infinity)
        - Graph connections between all segments
        - _segments_by_lane mapping for quick car position lookup
        """
        self._segments.clear()
        self._segments_by_lane.clear()
        self._graph.clear()

        horizontal_roads = sorted(
            self._horizontal_roads.values(), key=lambda r: r.position
        )
        vertical_roads = sorted(self._vertical_roads.values(), key=lambda r: r.position)

        crossing_map: dict[tuple[Lane, Lane], CrossingSegment] = {}

        for h_road in horizontal_roads:
            for v_road in vertical_roads:
                h_lanes = h_road.forward_lanes + h_road.backward_lanes
                v_lanes = v_road.forward_lanes + v_road.backward_lanes
                for h_lane in h_lanes:
                    for v_lane in v_lanes:
                        cs = CrossingSegment(
                            horizontal_lane=h_lane, vertical_lane=v_lane
                        )
                        self._segments[cs.uid] = cs
                        crossing_map[(h_lane, v_lane)] = cs

        for h_road in horizontal_roads:
            h_lanes = h_road.forward_lanes + h_road.backward_lanes
            h_lanes.sort(key=lambda l: l.get_one_dimensional_position(self))

            lane_physical_segments: dict[Lane, list[Segment]] = {}

            for lane in h_lanes:
                segments = []
                left_inf = LaneSegment(lane=lane)
                self._segments[left_inf.uid] = left_inf
                segments.append(left_inf)

                for v_road in vertical_roads:
                    v_lanes = sorted(
                        v_road.forward_lanes + v_road.backward_lanes,
                        key=lambda l: l.get_one_dimensional_position(self),
                    )
                    for v_lane in v_lanes:
                        segments.append(crossing_map[(lane, v_lane)])

                    mid_seg = LaneSegment(lane=lane)
                    self._segments[mid_seg.uid] = mid_seg
                    segments.append(mid_seg)

                lane_physical_segments[lane] = segments

                segments_uids = [s.uid for s in segments]
                self._segments_by_lane[lane] = segments_uids

                if lane.lane_index >= 0:
                    flow_uids = segments_uids
                    flow_dir = Direction.RIGHT
                else:
                    flow_uids = list(reversed(segments_uids))
                    flow_dir = Direction.LEFT

                for i in range(len(flow_uids) - 1):
                    self._graph.add_edge(
                        flow_uids[i], flow_uids[i + 1], direction=flow_dir
                    )

            for i in range(len(h_lanes) - 1):
                top_lane = h_lanes[i]
                bottom_lane = h_lanes[i + 1]

                segs_top = lane_physical_segments[top_lane]
                segs_bottom = lane_physical_segments[bottom_lane]

                for s_t, s_b in zip(segs_top, segs_bottom):
                    if isinstance(s_t, LaneSegment) and isinstance(s_b, LaneSegment):
                        self._graph.add_edge(s_t.uid, s_b.uid, direction=Direction.UP)
                        self._graph.add_edge(s_b.uid, s_t.uid, direction=Direction.DOWN)

        for v_road in vertical_roads:
            v_lanes = v_road.forward_lanes + v_road.backward_lanes
            v_lanes.sort(key=lambda l: l.get_one_dimensional_position(self))

            lane_physical_segments: dict[Lane, list[Segment]] = {}

            for lane in v_lanes:
                segments = []
                top_inf = LaneSegment(lane=lane)
                self._segments[top_inf.uid] = top_inf
                segments.append(top_inf)

                for h_road in horizontal_roads:
                    h_lanes = sorted(
                        h_road.forward_lanes + h_road.backward_lanes,
                        key=lambda l: l.get_one_dimensional_position(self),
                    )
                    for h_lane in h_lanes:
                        segments.append(crossing_map[(h_lane, lane)])

                    mid_seg = LaneSegment(lane=lane)
                    self._segments[mid_seg.uid] = mid_seg
                    segments.append(mid_seg)

                lane_physical_segments[lane] = segments

                segments_uids = [s.uid for s in segments]
                self._segments_by_lane[lane] = segments_uids

                if lane.lane_index >= 0:
                    flow_uids = segments_uids
                    flow_dir = Direction.UP
                else:
                    flow_uids = list(reversed(segments_uids))
                    flow_dir = Direction.DOWN

                for i in range(len(flow_uids) - 1):
                    self._graph.add_edge(
                        flow_uids[i], flow_uids[i + 1], direction=flow_dir
                    )

            for i in range(len(v_lanes) - 1):
                left_lane = v_lanes[i]
                right_lane = v_lanes[i + 1]

                segs_left = lane_physical_segments[left_lane]
                segs_right = lane_physical_segments[right_lane]

                for s_l, s_r in zip(segs_left, segs_right):
                    if isinstance(s_l, LaneSegment) and isinstance(s_r, LaneSegment):
                        self._graph.add_edge(
                            s_l.uid, s_r.uid, direction=Direction.RIGHT
                        )
                        self._graph.add_edge(s_r.uid, s_l.uid, direction=Direction.LEFT)

    def print_graph(self: "TrafficSnapshotModel") -> None:
        """
        Prints the graph structure for debugging.
        """
        print("=== Traffic Graph Structure ===")
        for segment_uid in self._graph.nodes:
            segment_info = self.get_segment_info(segment_uid, True)
            print(f"\n[Segment] {segment_info}")

            # Print outgoing connections
            out_edges = self._graph.out_edges(segment_uid, data=True)
            if not out_edges:
                print("  -> (no outgoing connections)")
            else:
                for _, target_uid, data in out_edges:
                    direction = data.get("direction")
                    direction_name = direction.name if direction else "UNKNOWN"
                    target_info = self.get_segment_info(target_uid)
                    print(f"  -> [{direction_name}] to {target_info}")
        print("===============================")

    def get_segment_info(self: "TrafficSnapshotModel", segment_uid: str, include_uid: bool = False) -> str:
        # maybe use polymorphism in the future to remove instance checks
        segment = self._segments.get(segment_uid)
        if segment is None:
            return f"unknown segment with uid {segment_uid}"

        def format_lane(lane: Lane) -> str:
            return lane.get_name(self)

        uid_suffix = f"({segment.uid})" if include_uid else ""
        if isinstance(segment, CrossingSegment):
            return (
                f"crossing{uid_suffix} "
                f"({format_lane(segment.horizontal_lane)}, "
                f"{format_lane(segment.vertical_lane)})"
            )

        elif isinstance(segment, LaneSegment):
            road = self.get_road_by_uid(segment.lane.road_uid)
            return f"lane{uid_suffix} at R{road.name}({format_lane(segment.lane)})"

        raise NotImplementedError(f"Unknown segment type: {type(segment)}")

    def debug_get_segments(self: "TrafficSnapshotModel") -> dict[str, Segment]:
        return self._debug_segments

    def print_segments_by_lane(self: "TrafficSnapshotModel"):
        for lane, segment_uids in self._segments_by_lane.items():
            road = self.get_road_by_uid(lane.road_uid)
            print(f"Lane {lane.lane_index} on Road {road.name} has segments:")
            for uid in segment_uids:
                segment = self._segments[uid]
                position = segment.get_position(self)
                size = segment.get_size(self)
                print(
                    f"  - {segment.uid}: {type(segment).__name__}, position={position}, size={size}"
                )
        pass
