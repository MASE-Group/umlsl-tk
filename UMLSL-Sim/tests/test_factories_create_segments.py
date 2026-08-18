"""Unit tests for `factories.create_segments` -- roads in, a segment graph out.

`create_segments` is the only thing that builds the world cars drive on, so its
output is the precondition of every other test in the suite: lane segments cut
at intersection boundaries, a crossing cell per lane pair, and each segment
wired to its successor in the lane's direction of travel.
"""

import unittest

from umlsl_sim.config.logic_constants import BLOCK_SIZE
from umlsl_sim.factories.create_segments import OverlappingRoadsError, create_segments
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    Direction,
    LaneSegment,
    Road,
)

from tests.helpers import ring_world, single_crossing_world, two_lane_world


class TestSegmentGraphShape(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()

    def test_one_pair_of_roads_makes_one_intersection(self):
        self.assertEqual(len(self.world.intersections), 1)

    def test_a_crossing_cell_exists_for_every_lane_pair(self):
        intersection = self.world.intersections[0]
        h_lanes = len(self.world.road("h1").right_lanes) + len(self.world.road("h1").left_lanes)
        v_lanes = len(self.world.road("v1").right_lanes) + len(self.world.road("v1").left_lanes)
        self.assertEqual(len(intersection.segments), h_lanes * v_lanes)

    def test_every_crossing_cell_is_a_crossing_segment(self):
        for intersection in self.world.intersections:
            for segment in intersection.segments:
                self.assertIsInstance(segment, CrossingSegment)

    def test_each_lane_owns_exactly_one_lane_segment_here(self):
        for road in self.world.roads:
            for lane in road.right_lanes + road.left_lanes:
                lane_segments = [s for s in lane.segments if isinstance(s, LaneSegment)]
                self.assertEqual(len(lane_segments), 1, f"{road.name} lane {lane.num}")

    def test_the_returned_list_holds_every_segment_of_every_lane(self):
        from_lanes = {id(s) for road in self.world.roads
                      for lane in road.right_lanes + road.left_lanes
                      for s in lane.segments}
        self.assertEqual({id(s) for s in self.world.segments}, from_lanes)

    def test_a_crossing_cell_is_shared_by_its_two_lanes(self):
        crossing = self.world.crossing_segments("h1", "right")[0]
        self.assertIn(crossing, crossing.horiz_lane.segments)
        self.assertIn(crossing, crossing.vert_lane.segments)

    def test_a_crossing_records_its_index_in_both_lanes(self):
        for segment in self.world.segments:
            if isinstance(segment, CrossingSegment):
                self.assertIs(segment.horiz_lane.segments[segment.horiz_num], segment)
                self.assertIs(segment.vert_lane.segments[segment.vert_num], segment)

    def test_every_crossing_belongs_to_the_intersection_that_lists_it(self):
        for intersection in self.world.intersections:
            for segment in intersection.segments:
                self.assertIs(segment.intersection, intersection)


class TestLaneSegmentGeometry(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()

    def test_a_forward_lane_segment_runs_from_low_to_high(self):
        segment = self.world.lane_segment("h1", "right")   # RIGHT
        self.assertLess(segment.begin, segment.end)

    def test_a_reverse_lane_segment_runs_from_high_to_low(self):
        segment = self.world.lane_segment("h1", "left")    # LEFT
        self.assertGreater(segment.begin, segment.end)

    def test_both_directions_of_one_road_span_the_same_length(self):
        forward = self.world.lane_segment("h1", "right")
        reverse = self.world.lane_segment("h1", "left")
        self.assertEqual(forward.length, reverse.length)

    def test_a_lane_segment_stops_where_the_crossing_road_starts(self):
        segment = self.world.lane_segment("h1", "right")
        self.assertEqual(max(segment.begin, segment.end), self.world.road("v1").top)

    def test_segment_numbers_index_into_the_lane(self):
        for road in self.world.roads:
            for lane in road.right_lanes + road.left_lanes:
                for segment in lane.segments:
                    if isinstance(segment, LaneSegment):
                        self.assertIs(lane.segments[segment.num], segment)


class TestSegmentConnectivity(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()

    def test_every_lane_segment_leads_into_a_crossing(self):
        for segment in self.world.lane_segments():
            self.assertIsInstance(segment.end_crossing, CrossingSegment)
            self.assertIsInstance(segment.begin_crossing, CrossingSegment)

    def test_a_crossing_has_an_exit_for_each_lane_through_it(self):
        for segment in self.world.segments:
            if isinstance(segment, CrossingSegment):
                exits = [d for d, s in segment.connected_segments.items() if s is not None]
                self.assertEqual(sorted(d.name for d in exits),
                                 sorted({segment.horiz_lane.direction.name,
                                         segment.vert_lane.direction.name}))

    def test_following_a_lane_forward_returns_to_where_it_started(self):
        """The graph closes: a car may drive the loop indefinitely."""
        start = self.world.lane_segment("h1", "right")
        direction = start.lane.direction
        current, steps = start.end_crossing, 1
        while current is not start and steps < 20:
            if isinstance(current, CrossingSegment):
                current = current.connected_segments[direction]
            else:
                direction = current.lane.direction
                current = current.end_crossing
            steps += 1
        self.assertIs(current, start, "the lane did not close into a cycle")

    def test_a_lane_segments_begin_crossing_leads_back_into_it(self):
        for segment in self.world.lane_segments():
            direction = segment.lane.direction
            self.assertIs(segment.begin_crossing.connected_segments[direction], segment)


class TestRingWorld(unittest.TestCase):
    """Four one-way roads: the smallest world with a forced route."""

    def setUp(self):
        self.world = ring_world()

    def test_four_roads_make_four_intersections(self):
        self.assertEqual(len(self.world.intersections), 4)

    def test_each_one_way_lane_holds_a_single_lane_segment(self):
        self.assertEqual(len(self.world.lane_segments()), 4)

    def test_each_lane_carries_one_segment_per_intersection_it_crosses(self):
        for road in self.world.roads:
            for lane in road.right_lanes + road.left_lanes:
                crossings = [s for s in lane.segments if isinstance(s, CrossingSegment)]
                self.assertEqual(len(crossings), 2)


class TestMultiLaneRoad(unittest.TestCase):

    def setUp(self):
        self.world = two_lane_world()

    def test_each_parallel_lane_gets_its_own_lane_segment(self):
        first = self.world.lane_segment("h1", "right", num=0)
        second = self.world.lane_segment("h1", "right", num=1)
        self.assertIsNot(first, second)

    def test_parallel_lane_segments_share_a_segment_number(self):
        first = self.world.lane_segment("h1", "right", num=0)
        second = self.world.lane_segment("h1", "right", num=1)
        self.assertEqual(first.num, second.num)

    def test_parallel_lane_segments_span_the_same_range(self):
        first = self.world.lane_segment("h1", "right", num=0)
        second = self.world.lane_segment("h1", "right", num=1)
        self.assertEqual((first.begin, first.end), (second.begin, second.end))

    def test_parallel_lanes_are_one_block_apart(self):
        lane0 = self.world.lane("h1", "right", 0)
        lane1 = self.world.lane("h1", "right", 1)
        self.assertEqual(lane1.top - lane0.top, BLOCK_SIZE)


class TestCreateSegmentsSideEffects(unittest.TestCase):
    """FIXED (FINDINGS #1): the builder used to reorder and double-build."""

    def test_the_callers_road_list_is_not_reordered(self):
        roads = [Road("h1", True, 200, 1, 1),
                 Road("v1", False, 100, 1, 1),
                 Road("h0", True, 0, 1, 0)]
        before = list(roads)
        create_segments(roads)
        self.assertEqual(roads, before,
                         "create_segments must not sort the list it was handed")

    def test_the_top_down_order_it_needs_is_still_applied_internally(self):
        # Roads handed over out of order must still produce a valid graph.
        roads = [Road("h1", True, 200, 1, 1), Road("v1", False, 100, 1, 1)]
        segments, intersections = create_segments(roads)
        self.assertEqual(len(intersections), 1)
        self.assertTrue(any(isinstance(s, LaneSegment) for s in segments))

    def test_building_twice_gives_the_same_graph_rather_than_a_doubled_one(self):
        roads = [Road("h1", True, 200, 1, 1), Road("v1", False, 200, 1, 1)]
        first, _ = create_segments(roads)
        second, _ = create_segments(roads)
        self.assertEqual(len(first), len(second))

    def test_building_twice_leaves_each_lane_with_one_set_of_segments(self):
        roads = [Road("h1", True, 200, 1, 1), Road("v1", False, 200, 1, 1)]
        create_segments(roads)
        counts = [len(l.segments) for r in roads for l in r.right_lanes + r.left_lanes]
        create_segments(roads)
        self.assertEqual([len(l.segments) for r in roads
                          for l in r.right_lanes + r.left_lanes], counts)

    def test_a_rebuild_replaces_the_segment_objects(self):
        roads = [Road("h1", True, 200, 1, 1), Road("v1", False, 200, 1, 1)]
        first, _ = create_segments(roads)
        second, _ = create_segments(roads)
        self.assertTrue({id(s) for s in first}.isdisjoint({id(s) for s in second}))


class TestOverlappingRoads(unittest.TestCase):

    def test_two_horizontal_roads_that_overlap_are_rejected(self):
        roads = [Road("h1", True, 0, 2, 2),      # spans 0 .. 160
                 Road("h2", True, 80, 1, 1),     # starts inside h1
                 Road("v1", False, 400, 1, 1)]
        with self.assertRaises(OverlappingRoadsError):
            create_segments(roads)

    def test_two_vertical_roads_that_overlap_are_rejected(self):
        roads = [Road("h1", True, 400, 1, 1),
                 Road("v1", False, 0, 2, 2),
                 Road("v2", False, 80, 1, 1)]
        with self.assertRaises(OverlappingRoadsError):
            create_segments(roads)

    def test_the_error_names_the_offending_road(self):
        roads = [Road("h1", True, 0, 2, 2), Road("h2", True, 80, 1, 1),
                 Road("v1", False, 400, 1, 1)]
        with self.assertRaises(OverlappingRoadsError) as ctx:
            create_segments(roads)
        self.assertIn("'h2'", str(ctx.exception))

    def test_roads_that_merely_touch_are_accepted(self):
        # h1 spans 0..80, h2 starts exactly at 80.
        roads = [Road("h1", True, 0, 1, 1), Road("h2", True, 80, 1, 1),
                 Road("v1", False, 400, 1, 1)]
        segments, _ = create_segments(roads)
        self.assertTrue(segments)

    def test_the_error_is_a_value_error(self):
        self.assertTrue(issubclass(OverlappingRoadsError, ValueError))


class TestDegenerateNetworks(unittest.TestCase):

    def test_roads_of_one_orientation_only_produce_nothing(self):
        """Lane segments are cut *at* intersections, so a network with no
        crossing road has no segments at all -- and therefore no capacity for
        cars. Documented so the empty result is not mistaken for a failure."""
        segments, intersections = create_segments([Road("h1", True, 0, 1, 1)])
        self.assertEqual(segments, [])
        self.assertEqual(intersections, [])

    def test_an_empty_network_is_accepted(self):
        self.assertEqual(create_segments([]), ([], []))

    def test_two_roads_both_at_the_top_produce_no_lane_segments(self):
        """A road at top 0 leaves no room before the first crossing, so the
        intersection exists but nothing leads into it."""
        roads = [Road("h", True, 0, 1, 0), Road("v", False, 0, 1, 0)]
        segments, intersections = create_segments(roads)
        self.assertEqual(len(intersections), 1)
        self.assertEqual([s for s in segments if isinstance(s, LaneSegment)], [])

    def test_a_road_with_no_lanes_contributes_nothing(self):
        roads = [Road("h1", True, 200, 1, 1),
                 Road("v1", False, 200, 1, 1),
                 Road("bare", True, 600, 0, 0)]
        segments, _ = create_segments(roads)
        self.assertTrue(all(getattr(s, "road", None) is not roads[2] for s in segments))


class TestCrossingDirections(unittest.TestCase):

    def test_a_crossing_leads_onwards_in_each_lanes_own_direction(self):
        world = single_crossing_world()
        for segment in world.segments:
            if not isinstance(segment, CrossingSegment):
                continue
            for direction, target in segment.connected_segments.items():
                if target is None:
                    continue
                self.assertIn(direction, (segment.horiz_lane.direction,
                                          segment.vert_lane.direction))

    def test_a_forward_lane_advances_and_a_reverse_lane_retreats(self):
        world = single_crossing_world()
        forward = world.lane("h1", "right")
        reverse = world.lane("h1", "left")
        self.assertIs(forward.direction, Direction.RIGHT)
        self.assertIs(reverse.direction, Direction.LEFT)
        forward_seg = world.lane_segment("h1", "right")
        reverse_seg = world.lane_segment("h1", "left")
        self.assertLess(forward_seg.begin, forward_seg.end)
        self.assertGreater(reverse_seg.begin, reverse_seg.end)


if __name__ == "__main__":
    unittest.main()
