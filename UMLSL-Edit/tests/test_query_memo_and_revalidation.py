"""
Regression tests for two performance shortcuts that must not change any result.

The horizontal chop remembers its verdict per observed space and binding of the variables, and a
chopped View filters its lanes only when they are read: deciding a formula with the memo disabled
has to give the same verdict. Adding or editing a car revalidates only that car, since a car's
validity and environment do not depend on the other cars: the other cars have to be left as they
are, while a change of a road still revalidates every car.
"""
import json
import os
import unittest
from unittest import mock

from umlsl_edit.controllers.command_controller import CommandController
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType
from umlsl_edit.query.evaluator import UMLSLEvaluator
from umlsl_edit.query.view import View

PAPER_EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "sample_scenes", "paper_example.json")

# {ego} is replaced by the name of each car in turn
FORMULAS = [
    "<re{{{ego}}}>",
    "<cl{{{ego}}}>",
    "<cs>",
    "<hchop{{re{{{ego}}}}}{{l > 2 and free}}>",
    "<hchop{{re{{{ego}}}}}{{free and (neg <cs>) and l > 2}}{{cs}}>",
    "<hchop{{hchop{{l >= 1 and l <= 1}}{{l >= 2 and l <= 2}}}}{{free}}>",
    "<hchop{{l <= 1 and free}}{{re{{{ego}}}}}>",
    "<hchop{{l >= 1 and l <= 1}}{{free and l > 100}}>",
    "forall c: (c != {ego} => neg <re{{{ego}}} and re{{c}}>)",
    "exists c: (c != {ego} and <hchop{{re{{{ego}}}}}{{free}}{{re{{c}}}}>)",
    "exists c: exists d: (c != d and <re{{c}} and re{{d}}>)",
]


class _Forgetful(dict):
    """A memo that stores nothing, so that every observed space is decided afresh."""

    def __setitem__(self, key, value):
        pass


def _memo_disabled():
    original_init = View.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        if not isinstance(self.memo, _Forgetful):
            self.memo = _Forgetful()  # the root; chopped Views are handed the root's memo

    return mock.patch.object(View, "__init__", init)


class TestChopMemo(unittest.TestCase):
    def setUp(self):
        self.settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        self.snapshot = TrafficSnapshotModel(settings_model=self.settings)
        with open(PAPER_EXAMPLE) as file:
            TrafficSnapshotModel.from_dict(json.load(file), self.snapshot, self.snapshot, self.settings)
        self.evaluator = UMLSLEvaluator(self.snapshot)

    def test_verdicts_match_without_memo(self):
        verdicts = set()
        for ego in self.snapshot.get_car_list():
            for template in FORMULAS:
                latex = template.format(ego=ego.name)
                for lane_only in (False, True):
                    with self.subTest(ego=ego.name, formula=latex, ego_lane_only=lane_only):
                        with_memo = self.evaluator.parse_ast(latex, ego).evaluate(lane_only)
                        with _memo_disabled():
                            without_memo = self.evaluator.parse_ast(latex, ego).evaluate(lane_only)
                        self.assertEqual(with_memo, without_memo)
                        verdicts.add(with_memo)
        # the formulas are not all decided the same way, so the comparison has something to compare
        self.assertEqual(verdicts, {True, False})

    def test_memo_is_used(self):
        # the left-nested chain re-decides its inner chops on prefixes the memo already holds
        ego = self.snapshot.get_car_by_name("E")
        stored = []
        original_init = View.__init__

        def init(view, *args, **kwargs):
            original_init(view, *args, **kwargs)
            if kwargs.get("memo") is None and len(args) < 10:
                stored.append(view.memo)

        latex = FORMULAS[5].format(ego="E")
        with mock.patch.object(View, "__init__", init):
            self.evaluator.parse_ast(latex, ego).evaluate(False)
        self.assertTrue(stored)
        self.assertTrue(any(len(memo) > 0 for memo in stored))


class TestRevalidationOfOneCar(unittest.TestCase):
    def setUp(self):
        self.settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        self.snapshot = TrafficSnapshotModel(settings_model=self.settings)
        queries = UMLSLQueriesModel(traffic_snapshot=self.snapshot)
        self.controller = CommandController(self.snapshot, self.snapshot, queries, self.settings)
        self.controller.add_road(
            name="Main", orientation=RoadOrientation.HORIZONTAL, position=0.0,
            number_of_forward_lanes=2, number_of_backward_lanes=1,
        )
        self.road = next(iter(self.snapshot.get_roads().values()))
        for name, lane, position in (("A", 0, 10.0), ("B", 1, 30.0), ("C", -1, 50.0)):
            self.add(name, lane, position)
        self.updated: list[str] = []
        self.snapshot.attach(self._record)

    def add(self, name: str, lane: int, position: float) -> None:
        self.controller.add_car(
            name=name, assigned_road=self.road, lane_index=lane, color="#ff0000",
            position_on_lane=position, transition=0.0, speed=5.0, length=4.0, acceleration=0.0,
            next_turn=None,
        )

    def _record(self, event_type, data=None) -> None:
        if event_type == TrafficSnapshotEventType.CAR_UPDATED:
            self.updated.append(data.name)

    def environments(self) -> dict:
        return {car.name: car.environment for car in self.snapshot.get_car_list()}

    def world_horizons(self) -> dict:
        """Each car's view along the road, in world coordinates (the lanes start at the west end of the world)."""
        west_end = -self.snapshot.get_world_extent()[0]
        return {car.name: (west_end + car.environment.horizon.start, west_end + car.environment.horizon.end)
                for car in self.snapshot.get_car_list()}

    def test_adding_a_car_leaves_the_others(self):
        # D's environment ends before C's does, so the world, and with it every other environment, stays as it is
        extent = self.snapshot.get_world_extent()
        before = self.environments()
        self.add("D", 0, 20.0)
        after = self.environments()
        self.assertIn("D", after)
        self.assertEqual(self.snapshot.get_world_extent(), extent)
        for name in ("A", "B", "C"):
            self.assertIs(after[name], before[name])
        self.assertTrue(set(self.updated) <= {"D"})

    def test_adding_a_car_past_every_environment_grows_the_world_but_changes_no_view(self):
        extent = self.snapshot.get_world_extent()
        before = self.world_horizons()
        self.add("D", 0, 70.0)
        self.assertGreater(self.snapshot.get_world_extent()[0], extent[0])
        after = self.world_horizons()
        for name in ("A", "B", "C"):
            self.assertEqual(after[name], before[name])
        # the others' outer lane segment moved, so their environments were rebuilt, but nothing about them changed
        self.assertTrue(set(self.updated) <= {"D"})

    def test_editing_a_car_leaves_the_others(self):
        before = self.environments()
        self.controller.edit_car(self.snapshot.get_car_by_name("B"), position_on_lane=35.0)
        after = self.environments()
        self.assertIsNot(after["B"], before["B"])
        self.assertEqual(after["B"].horizon.start - before["B"].horizon.start, 5.0)
        for name in ("A", "C"):
            self.assertIs(after[name], before[name])
        self.assertEqual(set(self.updated), {"B"})

    def test_a_road_change_still_revalidates_every_car(self):
        before = self.environments()
        self.controller.update_road(self.road, position=2.0)
        after = self.environments()
        for name in ("A", "B", "C"):
            self.assertIsNot(after[name], before[name])


if __name__ == "__main__":
    unittest.main()
