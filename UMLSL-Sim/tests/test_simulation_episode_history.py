"""Unit tests for `simulation.episode_history` -- recording and replaying a run.

A recording holds *actions*, so a replay re-drives them through the live `Car`
API rather than scrubbing stored coordinates. That only reproduces the episode
if the state it started from was captured too, which is what `CarSnapshot` and
the `ReservationManagement` argument to `set_list_of_cars` are for.
"""

import unittest

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.episode_history import (
    CarSnapshot,
    GameHistory,
    HistoryNotReplayable,
)
from umlsl_sim.simulation.ports import NullRenderer

from tests.helpers import place_car, single_crossing_world, two_lane_world


class _CountingRenderer(NullRenderer):
    """A `NullRenderer` that remembers how it was driven."""

    def __init__(self):
        super().__init__()
        self.bound = None
        self.frames = 0
        self.closed = False

    def bind(self, cars, roads, reservation_management=None):
        self.bound = (list(cars), list(roads), reservation_management)

    def draw_frame(self):
        self.frames += 1

    def close(self):
        super().close()
        self.closed = True


class _HistoryFixture(unittest.TestCase):
    """A world with two cars and a history recording them."""

    def setUp(self):
        Car.reset_id_counter()
        self.world = single_crossing_world()
        self.rm = self.world.reservation_management
        self.first = place_car(self.world, self.world.lane_segment("h1", "right"),
                               speed=5, size=40, name="First",
                               goal_segment=self.world.lane_segment("v1", "right"))
        self.second = place_car(self.world, self.world.lane_segment("v1", "left"),
                                speed=5, size=40, name="Second",
                                goal_segment=self.world.lane_segment("h1", "left"))
        self.cars = [self.first, self.second]
        self.history = GameHistory()
        self.history.set_map(self.world.roads)
        self.history.set_list_of_cars(self.cars, self.rm)


class TestGameHistoryRecording(_HistoryFixture):

    def test_a_fresh_history_is_empty(self):
        history = GameHistory()
        self.assertEqual(history.map, [])
        self.assertEqual(history.list_of_cars, [])
        self.assertEqual(history.action_history_dict, {})
        self.assertEqual(history.car_snapshots, [])
        self.assertEqual(history.action_length, 0)

    def test_the_map_is_copied_rather_than_aliased(self):
        self.world.roads.append(self.world.roads[0])
        self.assertNotEqual(len(self.history.map), len(self.world.roads))

    def test_the_car_list_is_copied_rather_than_aliased(self):
        self.cars.clear()
        self.assertEqual(len(self.history.list_of_cars), 2)

    def test_every_car_gets_an_action_entry(self):
        self.assertEqual(len(self.history.action_history_dict), 2)
        self.assertTrue(all(v == [] for v in self.history.action_history_dict.values()))

    def test_actions_are_appended_per_car(self):
        self.history.add_taken_action(self.first, (1, 0))
        self.history.add_taken_action(self.first, (-1, 1))
        self.history.add_taken_action(self.second, (0, 0))
        recorded = self.history.action_history_dict
        self.assertEqual(recorded[self.history._car_entry_key(self.first)],
                         [(1, 0), (-1, 1)])
        self.assertEqual(recorded[self.history._car_entry_key(self.second)], [(0, 0)])

    def test_the_action_count_totals_every_car(self):
        self.history.add_taken_action(self.first, (1, 0))
        self.history.add_taken_action(self.second, (1, 0))
        self.assertEqual(self.history.action_length, 2)

    def test_the_entry_key_is_built_from_the_unique_car_id(self):
        """FIXED (FINDINGS #7): the key used to be type + display *name*.

        A scenario may name two predefined cars alike, and a name-keyed history
        merged their action lists into one -- silently losing one car's record
        and double-counting the other's.
        """
        key = self.history._car_entry_key(self.first)
        self.assertIn(self.first.id, key)
        self.assertIn(self.first.type.name, key)

    def test_two_cars_with_the_same_name_keep_separate_records(self):
        Car.reset_id_counter()
        world = single_crossing_world()
        twins = [
            place_car(world, world.lane_segment("h1", "right"), name="Twin"),
            place_car(world, world.lane_segment("v1", "right"), name="Twin"),
        ]
        history = GameHistory()
        history.set_list_of_cars(twins, world.reservation_management)
        self.assertEqual(len(history.action_history_dict), 2)
        history.add_taken_action(twins[0], (1, 0))
        self.assertEqual(
            [len(v) for v in history.action_history_dict.values()].count(1), 1)

    def test_recording_for_an_unregistered_car_is_a_clear_error(self):
        stranger = place_car(self.world, self.world.lane_segment("h1", "left"),
                             name="Stranger")
        with self.assertRaises(KeyError) as ctx:
            self.history.add_taken_action(stranger, (0, 0))
        self.assertIn("set_list_of_cars", str(ctx.exception))

    def test_an_action_dict_can_be_installed_wholesale(self):
        self.history.set_action_history_dict({"k": [(0, 0)]})
        self.assertEqual(self.history.action_history_dict, {"k": [(0, 0)]})

    def test_reset_clears_everything(self):
        self.history.add_taken_action(self.first, (1, 0))
        self.history.reset_history()
        self.assertEqual(self.history.map, [])
        self.assertEqual(self.history.list_of_cars, [])
        self.assertEqual(self.history.action_history_dict, {})
        self.assertEqual(self.history.car_snapshots, [])
        self.assertEqual(self.history.action_length, 0)


class TestCarSnapshots(_HistoryFixture):

    def test_a_snapshot_is_taken_for_every_car(self):
        self.assertEqual(len(self.history.car_snapshots), 2)
        self.assertTrue(all(isinstance(s, CarSnapshot)
                            for s in self.history.car_snapshots))

    def test_a_snapshot_records_the_state_the_car_started_in(self):
        snapshot = self.history.car_snapshots[0]
        self.assertEqual(snapshot.name, self.first.name)
        self.assertEqual(snapshot.speed, self.first.speed)
        self.assertEqual(snapshot.size, self.first.size)
        self.assertEqual(snapshot.loc, self.first.loc)
        self.assertIs(snapshot.type, self.first.type)
        self.assertIs(snapshot.segment,
                      self.rm.get_car_reservation(self.first.id, 0).segment)

    def test_the_snapshot_key_matches_the_action_entry_key(self):
        for snapshot in self.history.car_snapshots:
            self.assertIn(snapshot.key, self.history.action_history_dict)

    def test_the_snapshot_is_frozen(self):
        with self.assertRaises(Exception):
            self.history.car_snapshots[0].speed = 99

    def test_without_the_reservation_book_no_snapshot_is_taken(self):
        history = GameHistory()
        history.set_list_of_cars(self.cars)
        self.assertEqual(history.car_snapshots, [])
        self.assertEqual(len(history.action_history_dict), 2,
                         "actions are still recorded, only replay is unavailable")

    def test_a_car_mid_crossing_makes_the_recording_unreplayable(self):
        """A restored end-of-episode pickle can hold a car on a crossing, which
        has no lane to rebuild it on -- see FINDINGS #7."""
        from umlsl_sim.simulation.road_network.road_network import CrossingSegment
        for _ in range(80):
            self.first.move(self.rm)
            if isinstance(self.rm.get_car_reservation(self.first.id, 0).segment,
                          CrossingSegment):
                break
        else:
            self.fail("the car never reached a crossing")
        history = GameHistory()
        history.set_list_of_cars(self.cars, self.rm)
        self.assertEqual(history.car_snapshots, [])

    def test_re_registering_replaces_the_previous_snapshots(self):
        self.history.set_list_of_cars(self.cars[:1], self.rm)
        self.assertEqual(len(self.history.car_snapshots), 1)


class TestReplay(_HistoryFixture):
    """FIXED (FINDINGS #8): `replay` used to raise before drawing anything.

    It called `car.reset()` (which no longer exists) and `move()` /
    `change_lane()` without a `ReservationManagement`.
    """

    def _record(self, ticks, action=(0, 0)):
        for _ in range(ticks):
            for car in self.cars:
                self.history.add_taken_action(car, action)

    def test_a_recording_without_initial_state_refuses_to_replay(self):
        history = GameHistory()
        history.set_map(self.world.roads)
        history.set_list_of_cars(self.cars)
        with self.assertRaises(HistoryNotReplayable) as ctx:
            history.replay()
        self.assertIn("no initial car state", str(ctx.exception))

    def test_a_replay_runs_headlessly_by_default(self):
        self._record(4)
        self.history.replay()

    def test_one_frame_is_drawn_per_tick(self):
        self._record(4)
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        self.assertEqual(renderer.frames, 4)

    def test_the_renderer_is_bound_and_then_closed(self):
        self._record(2)
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        self.assertIsNotNone(renderer.bound)
        self.assertTrue(renderer.closed)

    def test_the_replay_binds_rebuilt_cars_not_the_recorded_ones(self):
        self._record(2)
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        replayed, _, _ = renderer.bound
        self.assertEqual(len(replayed), len(self.cars))
        for car in replayed:
            self.assertNotIn(car, self.cars)

    def test_the_replay_uses_a_reservation_book_of_its_own(self):
        self._record(2)
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        _, _, reservation_management = renderer.bound
        self.assertIsNot(reservation_management, self.rm)

    def test_a_replay_does_not_disturb_the_live_simulation(self):
        self._record(3, action=(5, 0))
        before = [(car.loc, car.speed, car.time) for car in self.cars]
        self.history.replay()
        self.assertEqual([(car.loc, car.speed, car.time) for car in self.cars], before)

    def test_the_recorded_accelerations_are_applied(self):
        self._record(3, action=(5, 0))
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        replayed, _, _ = renderer.bound
        for car, snapshot in zip(replayed, self.history.car_snapshots):
            self.assertEqual(car.speed, min(snapshot.speed + 15, car.max_speed))

    def test_the_cars_actually_advance(self):
        self._record(3, action=(0, 0))
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        replayed, _, _ = renderer.bound
        for car in replayed:
            self.assertEqual(car.time, 3)

    def test_replaying_twice_gives_the_same_run(self):
        self._record(4, action=(2, 0))

        def run():
            renderer = _CountingRenderer()
            self.history.replay(renderer)
            replayed, _, _ = renderer.bound
            return [(car.loc, car.speed, car.time) for car in replayed]

        self.assertEqual(run(), run())

    def test_a_car_whose_record_ends_early_simply_stops_acting(self):
        for _ in range(4):
            self.history.add_taken_action(self.first, (0, 0))
        self.history.add_taken_action(self.second, (0, 0))
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        self.assertEqual(renderer.frames, 4)
        replayed, _, _ = renderer.bound
        self.assertEqual(replayed[0].time, 4)
        self.assertEqual(replayed[1].time, 1)

    def test_an_empty_recording_draws_nothing(self):
        renderer = _CountingRenderer()
        self.history.replay(renderer)
        self.assertEqual(renderer.frames, 0)
        self.assertTrue(renderer.closed)

    def test_a_recorded_lane_change_is_re_driven(self):
        Car.reset_id_counter()
        world = two_lane_world()
        rm = world.reservation_management
        car = place_car(world, world.lane_segment("h1", "right", num=0),
                        speed=5, size=40, name="Changer")
        history = GameHistory()
        history.set_map(world.roads)
        history.set_list_of_cars([car], rm)
        history.add_taken_action(car, (0, 1))
        for _ in range(4):
            history.add_taken_action(car, (0, 0))

        renderer = _CountingRenderer()
        history.replay(renderer)
        replayed, _, replay_rm = renderer.bound
        self.assertIs(replay_rm.get_car_reservation(replayed[0].id, 0).segment,
                      world.lane_segment("h1", "right", num=1))


if __name__ == "__main__":
    unittest.main()
