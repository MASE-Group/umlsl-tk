"""Unit tests for `factories.car_spec` -- the predefined-car description type.

`CarSpec` and `PositionRef` are what a scenario file parses into, so these tests
are the contract between `scenario.loader` and `factories.create_cars`.
"""

import unittest

from umlsl_sim.factories.car_spec import CarSpec, PositionRef, resolve_position
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.road_network.road_network import LaneSegment

from tests.helpers import single_crossing_world, two_lane_world


class TestPositionRefFromDict(unittest.TestCase):

    def test_all_four_fields_are_read(self):
        ref = PositionRef.from_dict(
            {"road": "h1", "direction": "right", "lane": 1, "position": 120})
        self.assertEqual((ref.road, ref.direction, ref.lane, ref.position),
                         ("h1", "right", 1, 120))

    def test_lane_and_position_are_coerced_to_int(self):
        ref = PositionRef.from_dict(
            {"road": "h1", "direction": "right", "lane": "2", "position": "150"})
        self.assertEqual((ref.lane, ref.position), (2, 150))
        self.assertIsInstance(ref.lane, int)
        self.assertIsInstance(ref.position, int)

    def test_every_field_is_required(self):
        for missing in ("road", "direction", "lane", "position"):
            data = {"road": "h1", "direction": "right", "lane": 0, "position": 0}
            del data[missing]
            with self.assertRaises(KeyError, msg=f"missing {missing} was accepted"):
                PositionRef.from_dict(data)


class TestCarSpecFromDict(unittest.TestCase):

    def test_an_empty_spec_defaults_to_an_npc_with_nothing_pinned(self):
        spec = CarSpec.from_dict({})
        self.assertIs(spec.type, CarType.NPC)
        for field in ("start", "speed", "max_speed", "first_goal",
                      "second_goal", "name", "size", "color"):
            self.assertIsNone(getattr(spec, field), field)

    def test_the_car_type_is_case_insensitive(self):
        for text in ("agent", "AGENT", "Agent"):
            self.assertIs(CarSpec.from_dict({"type": text}).type, CarType.AGENT)

    def test_an_unknown_car_type_is_rejected_with_a_helpful_message(self):
        with self.assertRaises(ValueError) as ctx:
            CarSpec.from_dict({"type": "TRUCK"})
        self.assertIn("TRUCK", str(ctx.exception))
        self.assertIn("NPC or AGENT", str(ctx.exception))

    def test_numeric_fields_are_coerced_to_int(self):
        spec = CarSpec.from_dict({"speed": "5", "max_speed": "18", "size": "40"})
        self.assertEqual((spec.speed, spec.max_speed, spec.size), (5, 18, 40))

    def test_an_explicit_null_numeric_stays_none(self):
        spec = CarSpec.from_dict({"speed": None, "max_speed": None, "size": None})
        self.assertIsNone(spec.speed)
        self.assertIsNone(spec.max_speed)
        self.assertIsNone(spec.size)

    def test_a_colour_list_becomes_a_tuple(self):
        spec = CarSpec.from_dict({"color": [1, 2, 3]})
        self.assertEqual(spec.color, (1, 2, 3))
        self.assertIsInstance(spec.color, tuple)

    def test_position_fields_are_parsed_into_position_refs(self):
        spec = CarSpec.from_dict({
            "start": {"road": "h1", "direction": "right", "lane": 0, "position": 10},
            "first_goal": {"road": "v1", "direction": "left", "lane": 0, "position": 20},
            "second_goal": {"road": "h1", "direction": "left", "lane": 0, "position": 30},
        })
        for ref in (spec.start, spec.first_goal, spec.second_goal):
            self.assertIsInstance(ref, PositionRef)
        self.assertEqual(spec.start.position, 10)
        self.assertEqual(spec.first_goal.road, "v1")

    def test_the_name_is_taken_verbatim(self):
        self.assertEqual(CarSpec.from_dict({"name": "Ambulance"}).name, "Ambulance")

    def test_a_directly_constructed_spec_defaults_the_same_way(self):
        spec = CarSpec()
        self.assertIs(spec.type, CarType.NPC)
        self.assertIsNone(spec.start)


class TestResolvePosition(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()
        self.roads = self.world.roads

    def test_a_position_resolves_to_the_segment_containing_it(self):
        segment, _ = resolve_position(
            self.roads, PositionRef("h1", "right", 0, 100))
        self.assertIsInstance(segment, LaneSegment)
        self.assertLessEqual(min(segment.begin, segment.end), 100)
        self.assertGreaterEqual(max(segment.begin, segment.end), 100)

    def test_the_offset_is_measured_from_the_segment_start(self):
        segment, offset = resolve_position(
            self.roads, PositionRef("h1", "right", 0, 100))
        self.assertEqual(offset, abs(100 - segment.begin))

    def test_the_offset_is_unsigned_even_on_a_reverse_lane(self):
        segment, offset = resolve_position(
            self.roads, PositionRef("h1", "left", 0, 50))
        self.assertGreater(segment.begin, segment.end, "expected a reverse lane")
        self.assertGreaterEqual(offset, 0)
        self.assertEqual(offset, segment.begin - 50)

    def test_direction_is_case_insensitive(self):
        for text in ("right", "RIGHT", "Right"):
            segment, _ = resolve_position(
                self.roads, PositionRef("h1", text, 0, 100))
            self.assertIsInstance(segment, LaneSegment)

    def test_the_lane_index_selects_among_parallel_lanes(self):
        world = two_lane_world()
        first, _ = resolve_position(world.roads, PositionRef("h1", "right", 0, 100))
        second, _ = resolve_position(world.roads, PositionRef("h1", "right", 1, 100))
        self.assertIsNot(first, second)
        self.assertEqual(first.lane.num, 0)
        self.assertEqual(second.lane.num, 1)

    def test_the_segment_boundaries_are_inclusive(self):
        segment = self.world.lane_segment("h1", "right")
        for position in (segment.begin, segment.end):
            resolved, _ = resolve_position(
                self.roads, PositionRef("h1", "right", 0, position))
            self.assertIs(resolved, segment)

    def test_an_unknown_road_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("nowhere", "right", 0, 10))
        self.assertIn("nowhere", str(ctx.exception))

    def test_an_unknown_direction_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("h1", "sideways", 0, 10))
        self.assertIn("'right' or 'left'", str(ctx.exception))

    def test_a_lane_index_out_of_range_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("h1", "right", 9, 10))
        self.assertIn("Lane index 9", str(ctx.exception))

    def test_a_negative_lane_index_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_position(self.roads, PositionRef("h1", "right", -1, 10))

    def test_a_position_off_the_lane_is_rejected_and_the_error_lists_the_ranges(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("h1", "right", 0, 100_000))
        message = str(ctx.exception)
        self.assertIn("100000", message)
        self.assertIn("lane segments cover", message)

    def test_the_error_names_the_axis_the_coordinate_is_on(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("h1", "right", 0, 100_000))
        self.assertIn("(x coordinate)", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            resolve_position(self.roads, PositionRef("v1", "right", 0, 100_000))
        self.assertIn("(y coordinate)", str(ctx.exception))

    def test_crossing_segments_are_skipped_when_searching_a_lane(self):
        segment, _ = resolve_position(
            self.roads, PositionRef("h1", "right", 0, 100))
        self.assertIsInstance(segment, LaneSegment)


if __name__ == "__main__":
    unittest.main()
