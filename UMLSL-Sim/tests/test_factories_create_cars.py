"""Unit tests for `factories.create_cars` -- placing cars on a road network.

Two placement policies share almost everything: `create_random_car` picks a free
lane segment, `create_predefined_car` honours whatever a `CarSpec` pins and falls
back to the random logic for the rest. Both must leave the world consistent --
every car anchored on a segment, its reservation registered, no two cars in the
same space.
"""

import random
import unittest

from umlsl_sim.config.logic_constants import (
    BLOCK_SIZE,
    CROSSING_MAX_SPEED,
    LANE_MAX_SPEED,
    MINIMAL_SPEED,
)
from umlsl_sim.factories.car_spec import CarSpec, PositionRef
from umlsl_sim.factories.create_cars import (
    _footprint,
    _free_lane_segments,
    _pick_name_color,
    create_goal,
    create_predefined_car,
    create_random_car,
    total_lane_segments,
)
from umlsl_sim.palettes.car_colors import selected_colors
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.road_network.road_network import (
    Direction,
    Goal,
    LaneSegment,
    Road,
    direction_sign,
)

from tests.helpers import ring_world, single_crossing_world, two_lane_world


class TestTotalLaneSegments(unittest.TestCase):

    def test_counts_only_lane_segments(self):
        world = single_crossing_world()
        self.assertEqual(total_lane_segments(world.roads), len(world.lane_segments()))

    def test_crossings_are_not_counted(self):
        world = single_crossing_world()
        self.assertLess(total_lane_segments(world.roads), len(world.segments))

    def test_an_unbuilt_network_has_no_capacity(self):
        self.assertEqual(total_lane_segments([Road("h", True, 0, 1, 1)]), 0)

    def test_an_empty_network_has_no_capacity(self):
        self.assertEqual(total_lane_segments([]), 0)

    def test_a_second_lane_adds_capacity(self):
        self.assertGreater(total_lane_segments(two_lane_world().roads),
                           total_lane_segments(single_crossing_world().roads))


class TestFootprint(unittest.TestCase):
    """The axis interval a car body occupies, matching `Car.update_position`."""

    def test_a_forward_car_extends_ahead_of_its_reference_point(self):
        self.assertEqual(_footprint(100, 20, 40, Direction.RIGHT), (120, 160))

    def test_a_reverse_car_extends_behind_it(self):
        self.assertEqual(_footprint(100, -20, 40, Direction.LEFT), (40, 80))

    def test_up_counts_as_a_forward_direction(self):
        self.assertEqual(_footprint(0, 10, 30, Direction.UP), (10, 40))

    def test_down_counts_as_a_reverse_direction(self):
        self.assertEqual(_footprint(0, -10, 30, Direction.DOWN), (-40, -10))

    def test_the_interval_is_always_the_cars_size_wide(self):
        for direction in Direction:
            lo, hi = _footprint(50, direction_sign[direction] * 25, 44, direction)
            self.assertEqual(hi - lo, 44)

    def test_the_interval_is_always_ordered_low_to_high(self):
        for direction in Direction:
            lo, hi = _footprint(50, direction_sign[direction] * 25, 44, direction)
            self.assertLess(lo, hi)


class TestPickNameColor(unittest.TestCase):

    def test_the_first_car_gets_the_first_selected_colour(self):
        name, color = _pick_name_color([])
        first = next(iter(selected_colors))
        self.assertEqual(name, first)
        self.assertEqual(color, selected_colors[first])

    def test_a_name_already_taken_is_skipped(self):
        world = single_crossing_world()
        first = next(iter(selected_colors))
        taken = _FakeCar(first)
        name, _ = _pick_name_color([taken])
        self.assertNotEqual(name, first)

    def test_names_stay_unique_across_a_full_palette(self):
        cars = []
        for _ in range(len(selected_colors)):
            name, _ = _pick_name_color(cars)
            cars.append(_FakeCar(name))
        self.assertEqual(len({c.name for c in cars}), len(selected_colors))

    def test_it_falls_through_to_the_large_palette_when_the_short_one_runs_out(self):
        cars = [_FakeCar(name) for name in selected_colors]
        name, color = _pick_name_color(cars)
        self.assertNotIn(name, selected_colors)
        self.assertNotEqual(name, "")

    def test_an_exhausted_palette_yields_a_nameless_black_car(self):
        """FLAGGED (FINDINGS #13): the exhaustion fallback is silent.

        Every colour name taken gives ("", (0, 0, 0)) -- an unnamed black car
        rather than an error. Unreachable in practice: the palettes hold 573
        names between them and the segment-capacity check in `TrafficEnv`
        refuses far fewer cars than that.
        """
        from umlsl_sim.palettes.color_names import colors
        cars = [_FakeCar(name) for name in list(selected_colors) + list(colors)]
        self.assertEqual(_pick_name_color(cars), ("", (0, 0, 0)))


class _FakeCar:
    """Just enough of a car for the name/colour picker, which reads only `name`."""

    def __init__(self, name):
        self.name = name


class TestFreeLaneSegments(unittest.TestCase):

    def setUp(self):
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management

    def test_every_segment_is_free_in_an_empty_world(self):
        free = _free_lane_segments(self.world.roads, [], self.rm)
        self.assertEqual(len(free), total_lane_segments(self.world.roads))

    def test_a_placed_car_removes_its_own_segment(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        anchor = self.rm.get_car_reservation(car.id, 0).segment
        free = _free_lane_segments(self.world.roads, [car], self.rm)
        self.assertNotIn(id(anchor), {id(s) for s in free})
        self.assertEqual(len(free), total_lane_segments(self.world.roads) - 1)

    def test_only_lane_segments_are_offered(self):
        free = _free_lane_segments(self.world.roads, [], self.rm)
        self.assertTrue(all(isinstance(s, LaneSegment) for s in free))


class TestCreateRandomCar(unittest.TestCase):

    def setUp(self):
        random.seed(1234)
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management

    def test_the_car_is_anchored_on_a_lane_segment(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        self.assertIsInstance(self.rm.get_car_reservation(car.id, 0).segment, LaneSegment)

    def test_it_starts_at_the_beginning_of_its_segment(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        self.assertEqual(car.loc, 0)

    def test_the_requested_type_is_honoured(self):
        car = create_random_car(self.world.roads, [], CarType.AGENT, self.rm)
        self.assertIs(car.type, CarType.AGENT)

    def test_the_car_faces_the_way_its_lane_runs(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        segment = self.rm.get_car_reservation(car.id, 0).segment
        self.assertIs(car.direction, segment.lane.direction)

    def test_speed_never_exceeds_the_cars_own_maximum(self):
        for _ in range(10):
            world = single_crossing_world()
            car = create_random_car(world.roads, [], CarType.NPC,
                                    world.reservation_management)
            self.assertLessEqual(car.speed, car.max_speed)
            self.assertGreaterEqual(car.speed, 1)

    def test_max_speed_stays_within_the_configured_band(self):
        for _ in range(10):
            world = single_crossing_world()
            car = create_random_car(world.roads, [], CarType.NPC,
                                    world.reservation_management)
            self.assertGreaterEqual(car.max_speed, MINIMAL_SPEED)
            self.assertLessEqual(car.max_speed, LANE_MAX_SPEED)

    def test_cars_alternate_between_the_fast_and_slow_speed_bands(self):
        # Even-indexed cars are drawn from the fast band, odd from the slow one.
        world = ring_world()
        rm = world.reservation_management
        cars = []
        for _ in range(4):
            cars.append(create_random_car(world.roads, cars, CarType.NPC, rm))
        self.assertGreaterEqual(cars[0].max_speed, CROSSING_MAX_SPEED)
        self.assertLessEqual(cars[1].max_speed, CROSSING_MAX_SPEED)

    def test_size_stays_within_the_configured_band(self):
        for _ in range(10):
            world = single_crossing_world()
            car = create_random_car(world.roads, [], CarType.NPC,
                                    world.reservation_management)
            self.assertGreaterEqual(car.size, BLOCK_SIZE // 2)
            self.assertLessEqual(car.size, 3 * BLOCK_SIZE // 2)

    def test_two_cars_never_share_an_anchor_segment(self):
        cars = []
        for _ in range(len(self.world.lane_segments())):
            cars.append(create_random_car(self.world.roads, cars, CarType.NPC, self.rm))
        anchors = [id(self.rm.get_car_reservation(c.id, 0).segment) for c in cars]
        self.assertEqual(len(set(anchors)), len(anchors))

    def test_each_car_gets_its_own_name_and_colour(self):
        cars = []
        for _ in range(len(self.world.lane_segments())):
            cars.append(create_random_car(self.world.roads, cars, CarType.NPC, self.rm))
        self.assertEqual(len({c.name for c in cars}), len(cars))

    def test_both_goals_are_placed(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        self.assertIsInstance(car.goal, Goal)
        self.assertIsInstance(car.second_goal, Goal)

    def test_the_goals_take_the_cars_colour(self):
        car = create_random_car(self.world.roads, [], CarType.NPC, self.rm)
        self.assertEqual(car.goal.color, car.color)
        self.assertEqual(car.second_goal.color, car.color)

    def test_a_full_network_is_refused_with_an_actionable_message(self):
        cars = []
        for _ in range(len(self.world.lane_segments())):
            cars.append(create_random_car(self.world.roads, cars, CarType.NPC, self.rm))
        with self.assertRaises(ValueError) as ctx:
            create_random_car(self.world.roads, cars, CarType.NPC, self.rm)
        message = str(ctx.exception)
        self.assertIn("already occupied", message)
        self.assertIn("lower `players`", message)

    def test_placement_is_reproducible_under_a_fixed_seed(self):
        def place():
            random.seed(99)
            Car.reset_id_counter()
            world = single_crossing_world()
            car = create_random_car(world.roads, [], CarType.NPC,
                                    world.reservation_management)
            anchor = world.reservation_management.get_car_reservation(car.id, 0).segment
            return car.name, car.speed, car.size, str(anchor)

        self.assertEqual(place(), place())


class TestCreatePredefinedCar(unittest.TestCase):

    def setUp(self):
        random.seed(2024)
        Car.reset_id_counter()
        self.world = two_lane_world()
        self.rm = self.world.reservation_management
        self.roads = self.world.roads

    def _spec(self, **kwargs) -> CarSpec:
        return CarSpec(**kwargs)

    def test_an_empty_spec_behaves_like_a_random_car(self):
        car = create_predefined_car(self._spec(), self.roads, [], self.rm)
        self.assertIsInstance(self.rm.get_car_reservation(car.id, 0).segment, LaneSegment)
        self.assertEqual(car.loc, 0)

    def test_an_explicit_start_puts_the_car_where_the_spec_says(self):
        spec = self._spec(start=PositionRef("h1", "right", 0, 120))
        car = create_predefined_car(spec, self.roads, [], self.rm)
        segment = self.rm.get_car_reservation(car.id, 0).segment
        self.assertEqual(segment.begin + car.loc, 120)

    def test_a_start_on_a_reverse_lane_is_signed_by_the_direction_of_travel(self):
        spec = self._spec(start=PositionRef("h1", "left", 0, 120))
        car = create_predefined_car(spec, self.roads, [], self.rm)
        segment = self.rm.get_car_reservation(car.id, 0).segment
        self.assertLess(car.loc, 0, "a LEFT lane accumulates loc negatively")
        self.assertEqual(segment.begin + car.loc, 120)

    def test_pinned_scalars_are_used_verbatim(self):
        spec = self._spec(speed=3, max_speed=17, size=44, name="Ambulance",
                          color=(1, 2, 3), type=CarType.AGENT)
        car = create_predefined_car(spec, self.roads, [], self.rm)
        self.assertEqual((car.speed, car.max_speed, car.size), (3, 17, 44))
        self.assertEqual(car.name, "Ambulance")
        self.assertEqual(car.color, (1, 2, 3))
        self.assertIs(car.type, CarType.AGENT)

    def test_a_pinned_name_without_a_colour_still_gets_a_colour(self):
        car = create_predefined_car(self._spec(name="Ambulance"), self.roads, [], self.rm)
        self.assertEqual(car.name, "Ambulance")
        self.assertIn(car.color, list(selected_colors.values()))

    def test_a_pinned_colour_without_a_name_still_gets_a_name(self):
        car = create_predefined_car(self._spec(color=(9, 9, 9)), self.roads, [], self.rm)
        self.assertEqual(car.color, (9, 9, 9))
        self.assertTrue(car.name)

    def test_pinned_goals_land_where_the_spec_says(self):
        spec = self._spec(
            first_goal=PositionRef("v1", "right", 0, 120),
            second_goal=PositionRef("h1", "left", 0, 80),
        )
        car = create_predefined_car(spec, self.roads, [], self.rm)
        self.assertEqual(car.goal.lane_segment.lane.road.name, "v1")
        self.assertEqual(car.second_goal.lane_segment.lane.road.name, "h1")

    def test_an_unpinned_goal_is_placed_randomly(self):
        spec = self._spec(first_goal=PositionRef("v1", "right", 0, 120))
        car = create_predefined_car(spec, self.roads, [], self.rm)
        self.assertIsInstance(car.second_goal, Goal)

    def test_a_pinned_first_goal_offset_is_honoured(self):
        spec = self._spec(first_goal=PositionRef("h1", "right", 0, 120))
        car = create_predefined_car(spec, self.roads, [], self.rm)
        self.assertEqual(car.goal.pos.x, 120)

    def test_two_cars_may_share_a_long_segment_at_different_positions(self):
        first = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 0), size=40),
            self.roads, [], self.rm)
        second = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 150), size=40),
            self.roads, [first], self.rm)
        self.assertIsNot(first, second)
        anchors = {id(self.rm.get_car_reservation(c.id, 0).segment)
                   for c in (first, second)}
        self.assertEqual(len(anchors), 1, "both should be on the same segment")

    def test_overlapping_footprints_on_one_segment_are_refused(self):
        first = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 100), size=40),
            self.roads, [], self.rm)
        with self.assertRaises(ValueError) as ctx:
            create_predefined_car(
                self._spec(start=PositionRef("h1", "right", 0, 120), size=40),
                self.roads, [first], self.rm)
        self.assertIn("overlaps existing car", str(ctx.exception))

    def test_bumper_to_bumper_placement_is_accepted(self):
        first = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 100), size=40),
            self.roads, [], self.rm)
        second = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 140), size=40),
            self.roads, [first], self.rm)
        self.assertIsNotNone(second)

    def test_a_car_on_a_parallel_lane_does_not_block_the_same_offset(self):
        first = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 100), size=40),
            self.roads, [], self.rm)
        second = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 1, 100), size=40),
            self.roads, [first], self.rm)
        self.assertIsNotNone(second)

    def test_without_a_size_the_whole_segment_is_treated_as_taken(self):
        """A spec that pins no size cannot have its footprint checked, so the
        coarse segment-level exclusion applies instead."""
        first = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 0)),
            self.roads, [], self.rm)
        with self.assertRaises(ValueError) as ctx:
            create_predefined_car(
                self._spec(start=PositionRef("h1", "right", 0, 180)),
                self.roads, [first], self.rm)
        self.assertIn("already occupied", str(ctx.exception))

    def test_a_full_network_is_refused_for_an_unpinned_start(self):
        world = single_crossing_world()
        rm = world.reservation_management
        cars = []
        for _ in range(len(world.lane_segments())):
            cars.append(create_random_car(world.roads, cars, CarType.NPC, rm))
        with self.assertRaises(ValueError) as ctx:
            create_predefined_car(CarSpec(name="Extra"), world.roads, cars, rm)
        self.assertIn("Give the car an explicit `start`", str(ctx.exception))

    def test_an_invalid_start_is_reported_by_resolve_position(self):
        spec = self._spec(start=PositionRef("nowhere", "right", 0, 0))
        with self.assertRaises(ValueError) as ctx:
            create_predefined_car(spec, self.roads, [], self.rm)
        self.assertIn("nowhere", str(ctx.exception))

    def test_the_reservation_is_registered_for_the_new_car(self):
        car = create_predefined_car(
            self._spec(start=PositionRef("h1", "right", 0, 40)), self.roads, [], self.rm)
        segment = self.rm.get_car_reservation(car.id, 0).segment
        self.assertIn(car.id, self.rm.get_cars_on_segment(segment))


class TestCreateGoal(unittest.TestCase):

    def setUp(self):
        random.seed(7)
        self.world = single_crossing_world()

    def test_a_goal_lands_on_a_lane_segment(self):
        car_segment = self.world.lane_segment("h1", "right")
        goal = create_goal((1, 2, 3), car_segment, self.world.roads)
        self.assertIsInstance(goal.lane_segment, LaneSegment)

    def test_the_goal_never_sits_on_the_cars_own_segment(self):
        car_segment = self.world.lane_segment("h1", "right")
        for _ in range(30):
            goal = create_goal((1, 2, 3), car_segment, self.world.roads)
            self.assertIsNot(goal.lane_segment, car_segment)

    def test_the_second_goal_avoids_the_first(self):
        car_segment = self.world.lane_segment("h1", "right")
        first = create_goal((1, 2, 3), car_segment, self.world.roads)
        for _ in range(30):
            second = create_goal((1, 2, 3), car_segment, self.world.roads, first)
            self.assertIsNot(second.lane_segment, first.lane_segment)
            self.assertIsNot(second.lane_segment, car_segment)

    def test_the_goal_carries_the_colour_it_was_given(self):
        goal = create_goal((7, 8, 9), self.world.lane_segment("h1", "right"),
                           self.world.roads)
        self.assertEqual(goal.color, (7, 8, 9))

    def test_a_goal_defaults_to_the_middle_of_its_segment(self):
        goal = create_goal((1, 2, 3), self.world.lane_segment("h1", "right"),
                           self.world.roads)
        self.assertIsNone(goal.loc)

    def test_a_network_too_small_to_hold_a_goal_is_refused(self):
        # Two roads with one lane each: after excluding the car's segment and
        # the first goal's, nothing is left.
        world = ring_world()
        car_segment = world.lane_segment("hb", "right")
        first = create_goal((1, 2, 3), car_segment, world.roads)
        # Squeeze further: a two-segment world has nothing left for a third pick.
        tiny = [Road("h1", True, 200, 1, 0), Road("v1", False, 200, 1, 0)]
        from umlsl_sim.factories.create_segments import create_segments
        create_segments(tiny)
        tiny_segments = [s for r in tiny for l in r.right_lanes + r.left_lanes
                         for s in l.segments if isinstance(s, LaneSegment)]
        first_goal = Goal(tiny_segments[1], (1, 2, 3))
        with self.assertRaises(ValueError) as ctx:
            create_goal((1, 2, 3), tiny_segments[0], tiny, first_goal)
        self.assertIn("too small", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
