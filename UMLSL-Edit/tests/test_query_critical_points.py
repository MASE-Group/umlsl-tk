"""
Regression tests for the critical points of the horizontal chop.

The horizontal chop has to try enough split positions that it finds a witness whenever one exists.
Endpoints of cars, reservations, claims and segments are not enough on their own: a formula that
constrains the length of the observed space is satisfied only by splits at a fixed distance from one
of its ends, and nested chops compose those distances.
"""
import unittest

from umlsl_edit.controllers.command_controller import CommandController
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.query.evaluator import UMLSLEvaluator


def build_single_lane_snapshot():
    settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
    command_controller = CommandController(snapshot, snapshot, queries, settings)
    command_controller.add_road(
        name="Main",
        orientation=RoadOrientation.HORIZONTAL,
        position=0.0,
        number_of_forward_lanes=1,
        number_of_backward_lanes=0,
    )
    road = next(iter(snapshot.get_roads().values()))
    command_controller.add_car(
        name="E",
        assigned_road=road,
        lane_index=0,
        color="#ff0000",
        position_on_lane=10.0,
        transition=0.0,
        speed=5.0,
        length=4.0,
        acceleration=0.0,
        next_turn=None,
    )
    return snapshot, next(iter(snapshot.get_cars().values()))


class TestHorizontalChopCriticalPoints(unittest.TestCase):
    def setUp(self):
        self.snapshot, self.car = build_single_lane_snapshot()
        self.evaluator = UMLSLEvaluator(self.snapshot)

    def check(self, latex: str) -> bool:
        return self.evaluator.parse_ast(latex, self.car).evaluate(evaluate_ego_lane_only=False)

    def view_length(self) -> float:
        low, high = 0.0, 1000.0
        for _ in range(60):
            middle = (low + high) / 2
            if self.check(f"l >= {middle}"):
                low = middle
            else:
                high = middle
        return low

    def test_exact_length_split_is_found_for_every_constant(self):
        # "l >= a and l <= a" pins the left operand to length exactly a, so the only witness is the
        # split at distance a from the start of the observed space. It is satisfiable for every a up
        # to the length of the view, and none of those splits is an interval endpoint.
        for tenths in range(1, 61):
            a = tenths / 10
            with self.subTest(a=a):
                self.assertTrue(self.check(f"hchop{{l >= {a} and l <= {a}}}{{true}}"))

    def test_nested_chops_compose_their_length_constants(self):
        # Two nested chops each pinned to length 1 need witnesses at distance 1 and at distance 2
        # from the start, so the constants have to be composed rather than only offset from an end.
        self.assertTrue(
            self.check("hchop{hchop{l >= 1 and l <= 1}{l >= 1 and l <= 1}}{true}")
        )
        self.assertTrue(
            self.check("hchop{hchop{l >= 0.7 and l <= 0.7}{l >= 1.3 and l <= 1.3}}{true}")
        )

    def test_length_constraint_beyond_the_view_is_unsatisfiable(self):
        # Soundness in the other direction: the search must not invent witnesses.
        too_long = self.view_length() + 1.0
        self.assertFalse(self.check(f"hchop{{l >= {too_long}}}{{l >= {too_long}}}"))

    def test_chop_is_still_sound_for_unsatisfiable_length_conjunctions(self):
        self.assertFalse(self.check("hchop{l >= 2 and l <= 1}{true}"))


if __name__ == "__main__":
    unittest.main()
