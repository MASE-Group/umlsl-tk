"""Unit tests for `simulation.road_network.road_network` -- the world's geometry.

Nothing here moves; these are the shapes everything else is measured against.
"""

import unittest

from umlsl_sim.config.logic_constants import BLOCK_SIZE, CROSSING_MAX_SPEED, LANE_MAX_SPEED
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    Direction,
    Goal,
    Intersection,
    Lane,
    LaneSegment,
    Point,
    Problem,
    Road,
    SegmentInfo,
    clock_wise,
    direction_axis,
    direction_sign,
    horiz_direction,
    right_direction,
    true_direction,
)

from tests.helpers import TEST_COLOR, single_crossing_world


class TestDirectionTables(unittest.TestCase):
    """The four lookup tables every offset calculation in the simulator uses."""

    def test_every_direction_is_in_every_table(self):
        for table in (direction_axis, true_direction, horiz_direction,
                      right_direction, direction_sign):
            self.assertEqual(set(table), set(Direction))

    def test_true_direction_marks_increasing_axes(self):
        # RIGHT increases x, UP increases y; LEFT and DOWN decrease theirs.
        self.assertTrue(true_direction[Direction.RIGHT])
        self.assertTrue(true_direction[Direction.UP])
        self.assertFalse(true_direction[Direction.LEFT])
        self.assertFalse(true_direction[Direction.DOWN])

    def test_direction_sign_agrees_with_true_direction(self):
        for direction in Direction:
            expected = 1 if true_direction[direction] else -1
            self.assertEqual(direction_sign[direction], expected)

    def test_direction_sign_agrees_with_axis_step(self):
        for direction in Direction:
            dx, dy = direction_axis[direction]
            step = dx if horiz_direction[direction] else dy
            self.assertEqual(step, direction_sign[direction])

    def test_horiz_direction_marks_the_horizontal_pair(self):
        self.assertTrue(horiz_direction[Direction.RIGHT])
        self.assertTrue(horiz_direction[Direction.LEFT])
        self.assertFalse(horiz_direction[Direction.UP])
        self.assertFalse(horiz_direction[Direction.DOWN])

    def test_right_direction_marks_the_forward_side_of_each_road(self):
        # A horizontal road's right lanes run RIGHT; a vertical road's run DOWN.
        self.assertTrue(right_direction[Direction.RIGHT])
        self.assertTrue(right_direction[Direction.DOWN])
        self.assertFalse(right_direction[Direction.LEFT])
        self.assertFalse(right_direction[Direction.UP])

    def test_clock_wise_is_a_full_turn(self):
        self.assertEqual(clock_wise, [Direction.RIGHT, Direction.DOWN,
                                      Direction.LEFT, Direction.UP])
        self.assertEqual(len(set(clock_wise)), len(Direction))


class TestRoad(unittest.TestCase):

    def test_lane_counts_and_directions_on_a_horizontal_road(self):
        road = Road("h", horizontal=True, top=100, right=2, left=3)
        self.assertEqual(len(road.right_lanes), 2)
        self.assertEqual(len(road.left_lanes), 3)
        self.assertTrue(all(l.direction is Direction.RIGHT for l in road.right_lanes))
        self.assertTrue(all(l.direction is Direction.LEFT for l in road.left_lanes))

    def test_lane_directions_on_a_vertical_road(self):
        road = Road("v", horizontal=False, top=100, right=1, left=1)
        self.assertIs(road.right_lanes[0].direction, Direction.DOWN)
        self.assertIs(road.left_lanes[0].direction, Direction.UP)

    def test_right_lanes_are_stacked_one_block_apart_from_the_top(self):
        road = Road("h", horizontal=True, top=100, right=3, left=0)
        self.assertEqual([l.top for l in road.right_lanes],
                         [100, 100 + BLOCK_SIZE, 100 + 2 * BLOCK_SIZE])

    def test_left_lanes_start_below_the_right_lanes(self):
        road = Road("h", horizontal=True, top=0, right=2, left=1)
        self.assertGreaterEqual(road.left_lanes[0].top,
                                road.right_lanes[-1].top + BLOCK_SIZE)

    def test_bottom_spans_one_block_per_lane(self):
        road = Road("h", horizontal=True, top=60, right=2, left=3)
        self.assertEqual(road.bottom, 60 + 5 * BLOCK_SIZE)

    def test_a_road_with_no_lanes_has_zero_width(self):
        road = Road("empty", horizontal=True, top=40, right=0, left=0)
        self.assertEqual(road.right_lanes, [])
        self.assertEqual(road.left_lanes, [])
        self.assertEqual(road.bottom, road.top)

    def test_every_lane_knows_the_road_it_belongs_to(self):
        road = Road("h", horizontal=True, top=0, right=1, left=1)
        for lane in road.right_lanes + road.left_lanes:
            self.assertIs(lane.road, road)

    def test_lanes_are_numbered_from_zero_within_each_side(self):
        road = Road("h", horizontal=True, top=0, right=3, left=2)
        self.assertEqual([l.num for l in road.right_lanes], [0, 1, 2])
        self.assertEqual([l.num for l in road.left_lanes], [0, 1])


class TestRoadGetOuterLaneSegment(unittest.TestCase):
    """`Road.get_outer_lane_segment` -- dead code, pinned so a change is noticed.

    Nothing in the package calls this (see FINDINGS #12). The tests below record
    what it does today rather than endorsing it as an interface.
    """

    def setUp(self):
        self.world = single_crossing_world()

    def test_returns_the_same_numbered_segment_of_the_outermost_lane(self):
        road = self.world.road("h1")
        probe = self.world.lane_segment("h1", "right")
        outer = road.get_outer_lane_segment(probe, right_lanes=True)
        self.assertIs(outer, road.right_lanes[0].segments[probe.num])

    def test_left_side_reads_from_the_last_left_lane(self):
        road = self.world.road("h1")
        probe = self.world.lane_segment("h1", "right")
        outer = road.get_outer_lane_segment(probe, right_lanes=False)
        self.assertIs(outer, road.left_lanes[-1].segments[probe.num])

    def test_returns_none_when_that_side_has_no_lanes(self):
        road = Road("oneway", horizontal=True, top=0, right=1, left=0)
        probe = self.world.lane_segment("h1", "right")
        self.assertIsNone(road.get_outer_lane_segment(probe, right_lanes=False))

    def test_indexes_by_segment_number_so_a_crossing_can_select_a_lane_segment(self):
        # The parameter is typed `Segment`, and only `.num` is read -- which a
        # CrossingSegment does not have. Documented as a latent AttributeError.
        road = self.world.road("h1")
        crossing = self.world.crossing_segments("h1", "right")[0]
        with self.assertRaises(AttributeError):
            road.get_outer_lane_segment(crossing, right_lanes=True)


class TestLane(unittest.TestCase):

    def test_a_new_lane_has_no_segments(self):
        road = Road("h", horizontal=True, top=0, right=1, left=0)
        self.assertEqual(road.right_lanes[0].segments, [])

    def test_lane_records_what_it_was_built_with(self):
        road = Road("h", horizontal=True, top=0, right=1, left=0)
        lane = Lane(road, num=4, direction=Direction.LEFT, top=120)
        self.assertEqual((lane.num, lane.top), (4, 120))
        self.assertIs(lane.direction, Direction.LEFT)
        self.assertIs(lane.road, road)


class TestLaneSegment(unittest.TestCase):

    def setUp(self):
        self.road = Road("h", horizontal=True, top=80, right=1, left=1)
        self.forward_lane = self.road.right_lanes[0]
        self.reverse_lane = self.road.left_lanes[0]

    def test_length_is_absolute_so_a_reverse_segment_is_not_negative(self):
        forward = LaneSegment(self.forward_lane, 100, 300, 0)
        reverse = LaneSegment(self.reverse_lane, 300, 100, 0)
        self.assertEqual(forward.length, 200)
        self.assertEqual(reverse.length, 200)

    def test_max_speed_is_the_lane_limit(self):
        segment = LaneSegment(self.forward_lane, 0, 100, 0)
        self.assertEqual(segment.max_speed, LANE_MAX_SPEED)

    def test_crossings_start_unattached(self):
        segment = LaneSegment(self.forward_lane, 0, 100, 0)
        self.assertIsNone(segment.end_crossing)
        self.assertIsNone(segment.begin_crossing)

    def test_horizontal_segment_takes_its_x_from_begin_and_y_from_the_lane(self):
        segment = LaneSegment(self.forward_lane, 100, 300, 0)
        self.assertEqual(segment.h_begin, 100)
        self.assertEqual(segment.v_begin, self.forward_lane.top)

    def test_vertical_segment_swaps_those_axes(self):
        road = Road("v", horizontal=False, top=40, right=1, left=0)
        lane = road.right_lanes[0]
        segment = LaneSegment(lane, 100, 300, 0)
        self.assertEqual(segment.h_begin, lane.top)
        self.assertEqual(segment.v_begin, 100)

    def test_str_identifies_road_direction_lane_and_number(self):
        segment = LaneSegment(self.forward_lane, 0, 100, 3)
        self.assertEqual(str(segment), "h:RIGHT:0:3")

    def test_segment_knows_its_road(self):
        segment = LaneSegment(self.forward_lane, 0, 100, 0)
        self.assertIs(segment.road, self.road)


class TestCrossingSegment(unittest.TestCase):

    def setUp(self):
        self.h_road = Road("h", horizontal=True, top=0, right=1, left=0)
        self.v_road = Road("v", horizontal=False, top=200, right=1, left=0)
        self.intersection = Intersection(self.h_road, self.v_road)
        self.crossing = CrossingSegment(self.h_road.right_lanes[0],
                                        self.v_road.right_lanes[0],
                                        self.intersection)

    def test_a_crossing_is_one_block_square(self):
        self.assertEqual(self.crossing.length, BLOCK_SIZE)

    def test_max_speed_is_the_crossing_limit(self):
        self.assertEqual(self.crossing.max_speed, CROSSING_MAX_SPEED)

    def test_all_four_exits_start_unconnected(self):
        self.assertEqual(set(self.crossing.connected_segments), set(Direction))
        self.assertTrue(all(v is None for v in self.crossing.connected_segments.values()))

    def test_position_comes_from_the_two_lanes_it_joins(self):
        self.assertEqual(self.crossing.h_begin, self.v_road.right_lanes[0].top)
        self.assertEqual(self.crossing.v_begin, self.h_road.right_lanes[0].top)

    def test_str_names_both_lanes(self):
        self.assertEqual(str(self.crossing), "(h:RIGHT:0, v:DOWN:0)")

    def test_a_fresh_crossing_holds_no_departure_times(self):
        self.assertIsNone(self.crossing.crossing_segment_state.get_time_to_leave("anyone"))


class TestCrossingSegmentGetRoad(unittest.TestCase):
    """`CrossingSegment.get_road` -- dead code, pinned (see FINDINGS #12)."""

    def setUp(self):
        self.h_road = Road("h", horizontal=True, top=0, right=1, left=0)
        self.v_road = Road("v", horizontal=False, top=200, right=1, left=0)
        self.crossing = CrossingSegment(self.h_road.right_lanes[0],
                                        self.v_road.right_lanes[0],
                                        Intersection(self.h_road, self.v_road))

    def test_a_horizontal_direction_selects_the_horizontal_road(self):
        self.assertIs(self.crossing.get_road(Direction.RIGHT), self.h_road)
        self.assertIs(self.crossing.get_road(Direction.LEFT), self.h_road)

    def test_a_vertical_direction_selects_the_vertical_road(self):
        self.assertIs(self.crossing.get_road(Direction.UP), self.v_road)
        self.assertIs(self.crossing.get_road(Direction.DOWN), self.v_road)

    def test_opposite_flips_the_selection(self):
        self.assertIs(self.crossing.get_road(Direction.RIGHT, opposite=True), self.v_road)
        self.assertIs(self.crossing.get_road(Direction.UP, opposite=True), self.h_road)


class TestIntersection(unittest.TestCase):

    def test_a_new_intersection_holds_no_segments_and_no_claims(self):
        h_road = Road("h", horizontal=True, top=0, right=1, left=0)
        v_road = Road("v", horizontal=False, top=200, right=1, left=0)
        intersection = Intersection(h_road, v_road)
        self.assertEqual(intersection.segments, [])
        self.assertEqual(intersection.intersection_state.get_priority_items(), [])

    def test_str_reports_both_roads_and_the_segment_count(self):
        world = single_crossing_world()
        intersection = world.intersections[0]
        text = str(intersection)
        self.assertIn("Horizontal: h1", text)
        self.assertIn("Vertical: v1", text)
        self.assertIn(str(len(intersection.segments)), text)


class TestSegmentInfo(unittest.TestCase):

    def test_records_its_span_and_defaults_to_no_turn(self):
        world = single_crossing_world()
        segment = world.lane_segment("h1", "right")
        info = SegmentInfo(segment, 10, 90, Direction.RIGHT)
        self.assertEqual((info.begin, info.end), (10, 90))
        self.assertIs(info.direction, Direction.RIGHT)
        self.assertFalse(info.turn)

    def test_turn_is_settable_at_construction(self):
        world = single_crossing_world()
        segment = world.lane_segment("h1", "right")
        self.assertTrue(SegmentInfo(segment, 0, 10, Direction.RIGHT, True).turn)

    def test_str_shows_the_span(self):
        world = single_crossing_world()
        info = SegmentInfo(world.lane_segment("h1", "right"), 10, 90, Direction.RIGHT)
        self.assertIn("begin = 10, end = 90", str(info))


class TestGoal(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()

    def test_default_loc_places_the_goal_at_the_segment_midpoint(self):
        segment = self.world.lane_segment("h1", "right")
        goal = Goal(segment, TEST_COLOR)
        self.assertEqual(goal.pos.x, (segment.begin + segment.end) // 2)
        self.assertEqual(goal.pos.y, segment.lane.top + BLOCK_SIZE // 2)

    def test_an_explicit_loc_is_an_offset_along_the_direction_of_travel(self):
        segment = self.world.lane_segment("h1", "right")   # begin 0, runs RIGHT
        goal = Goal(segment, TEST_COLOR, loc=60)
        self.assertEqual(goal.pos.x, segment.begin + 60)

    def test_loc_runs_backwards_on_a_reverse_lane(self):
        segment = self.world.lane_segment("h1", "left")    # begin 200, runs LEFT
        goal = Goal(segment, TEST_COLOR, loc=60)
        self.assertEqual(goal.pos.x, segment.begin - 60)

    def test_a_goal_on_a_vertical_road_swaps_the_axes(self):
        segment = self.world.lane_segment("v1", "right")
        goal = Goal(segment, TEST_COLOR, loc=60)
        self.assertEqual(goal.pos.x, segment.lane.top + BLOCK_SIZE // 2)
        self.assertEqual(goal.pos.y, segment.begin - 60)   # DOWN lane

    def test_update_lane_segment_moves_the_goal(self):
        first = self.world.lane_segment("h1", "right")
        second = self.world.lane_segment("v1", "right")
        goal = Goal(first, TEST_COLOR)
        goal.update_lane_segment(second)
        self.assertIs(goal.lane_segment, second)
        self.assertEqual(goal.pos.x, second.lane.top + BLOCK_SIZE // 2)

    def test_the_colour_is_kept_as_given(self):
        goal = Goal(self.world.lane_segment("h1", "right"), TEST_COLOR)
        self.assertEqual(goal.color, TEST_COLOR)


class TestPointAndProblem(unittest.TestCase):

    def test_point_is_a_plain_pair(self):
        self.assertEqual(Point(3, 4), Point(3, 4))
        self.assertNotEqual(Point(3, 4), Point(4, 3))

    def test_problem_members_are_distinct(self):
        self.assertEqual(len({p.value for p in Problem}), len(Problem))

    def test_only_three_problem_members_are_ever_produced(self):
        """The rest are unreachable -- see FINDINGS #12.

        `Car.change_lane` is the only producer of `Problem`, and it returns
        exactly CHANGE_LANE_WHILE_CROSSING and NO_ADJACENT_LANE. The other four
        members are declared and never constructed anywhere in the package.
        """
        produced = {Problem.CHANGE_LANE_WHILE_CROSSING, Problem.NO_ADJACENT_LANE}
        unreachable = set(Problem) - produced
        self.assertEqual(
            {p.name for p in unreachable},
            {"NO_NEXT_SEGMENT", "SLOWER_WHILE_0", "FASTER_WHILE_MAX", "LANE_TOO_SHORT"},
        )


if __name__ == "__main__":
    unittest.main()
