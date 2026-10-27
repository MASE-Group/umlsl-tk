"""
Checks of the model checker against the semantics of UMLSL on traffic scenarios.

Every expected value is derived by hand from the geometry of the scenario and the satisfaction relation of
UMLSL: an observed space (L, [b, e]) is a set of lanes and an interval along them; the atoms need a single
lane and a space of positive length (spaces that merely touch do not overlap); the quantifiers range over
the cars whose reservation or claim overlaps ego's view; free is the derived formula neg exists c: <re(c) or
cl(c)>; vchop{upper}{lower} puts its first operand on the lanes to ego's left, relative to ego's driving
direction; and the view is a single one, in which every virtual lane follows one path.

Common settings: lane width 1, maximal deceleration 2 and maximal speed 6, so the view reaches
h = 6^2 / (2 * 2) = 9 behind and ahead of ego, and a car of length 1 with speed v and its rear at p reserves
[p, p + 1 + v^2/4] in its driving direction (plus its path through a crossing and its length beyond it, if
that reaches into one). World coordinates: x grows to the east and y to the north. On a horizontal road, r1
is the inner eastbound lane and l1 the inner westbound one, north of it; on a vertical road, u1 is the inner
northbound lane and d1 the inner southbound one, west of it.
"""
import unittest

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.query.evaluator import UMLSLEvaluator


def road(name, orientation, position, forward_lanes, backward_lanes):
    return {"uid": name, "name": name, "orientation": orientation, "position": float(position),
            "number_of_forward_lanes": forward_lanes, "number_of_backward_lanes": backward_lanes}


def car(name, road_name, lane_index, position, speed, transition=0.0, turn=None):
    """turn: None or (direction, target road, target lane index)"""
    next_turn = None
    if turn is not None:
        direction, target_road, target_lane = turn
        next_turn = {"direction": direction, "target_lane": {"road_uid": target_road, "lane_index": target_lane}}
    return {"uid": name, "name": name, "road_uid": road_name, "lane_index": lane_index,
            "position_on_lane": float(position), "transition": float(transition), "speed": float(speed),
            "length": 1.0, "color": "#ff0000", "acceleration": 0.0, "next_turn": next_turn}


def build_snapshot(roads, cars):
    settings = SettingsModel(braking_acceleration=2.0, max_speed=6.0)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    TrafficSnapshotModel.from_dict({"roads": roads, "cars": cars}, snapshot, snapshot, settings)
    return snapshot


class UMLSLSemanticsTestCase(unittest.TestCase):
    roads: list = []
    cars: list = []

    @classmethod
    def setUpClass(cls):
        cls.snapshot = build_snapshot(cls.roads, cls.cars)

    def holds(self, ego: str, query: str, ego_lane_only: bool = False, snapshot=None) -> bool:
        snapshot = snapshot or self.snapshot
        ego_car = next(c for c in snapshot.get_car_list() if c.name == ego)
        return UMLSLEvaluator(snapshot).parse_ast(query, ego_car).evaluate(ego_lane_only)

    def check(self, ego: str, cases: list[tuple[str, bool]], snapshot=None):
        for query, expected in cases:
            with self.subTest(ego=ego, query=query):
                self.assertEqual(self.holds(ego, query, snapshot=snapshot), expected)


class TestStraightRoad(UMLSLSemanticsTestCase):
    """
    Horizontal road with lanes l1 (westbound), r1 and r2 (eastbound), from north to south.
      E on r1, rear x=0, v=4  -> RE(E) = x in [0, 5]
      B on l1, rear x=6, v=4  -> RE(B) = x in [1, 6] (westbound: front at 5, braking to 1)
      C on r2, rear x=-3, v=2 -> RE(C) = x in [-3, -1]
    V(E) has the lanes l1, r1, r2 from E's left to E's right and X = x in [-9, 9].
    V(B) has the lanes r1, l1 from B's left to B's right (r2 is two lanes away) and X = x in [-3, 15].
    """
    roads = [road("R1", "HORIZONTAL", 0, 2, 1)]
    cars = [car("E", "R1", 0, 0, 4), car("B", "R1", -1, 6, 4), car("C", "R1", 1, -3, 2)]

    def test_reservation_and_its_length(self):
        self.check("E", [
            ("<re{E}>", True),
            ("<re{E} and l >= 5>", True),  # RE(E) is exactly 5 long
            ("<re{E} and l > 5>", False),
        ])

    def test_vertical_chop(self):
        self.check("E", [
            ("<vchop{re{B}}{re{E}}>", True),   # B reserves [1, 6] on E's left, above E's [0, 5]
            ("<vchop{re{E}}{re{B}}>", False),  # l1 is above r1, not below
            ("<vchop{re{E}}{re{C}}>", False),  # C's [-3, -1] and E's [0, 5] do not overlap along the road
            ("<hchop{re{C}}{re{E}}>", False),  # different lanes: a horizontal chop stays on one lane
        ])

    def test_vertical_chop_is_relative_to_the_driving_direction(self):
        # B drives west, so r1 (E's lane) is on B's left, i.e. above B
        self.check("B", [
            ("<vchop{re{E}}{re{B}}>", True),
            ("<vchop{re{B}}{re{E}}>", False),
        ])

    def test_free_space(self):
        self.check("E", [
            ("<hchop{re{E}}{free}>", True),                            # r1 is free in [5, 9]
            ("<hchop{free and l >= 9 and l <= 9}{re{E}}>", True),      # r1 is free in [-9, 0], 9 long
            ("<hchop{free and l >= 9.5 and l <= 9.5}{re{E}}>", False),  # the view starts at -9
            ("<vchop{hchop{free}{re{B}}}{hchop{re{E}}{free}}>", True),  # on [0.5, 5.5]
            ("hchop{free}{true}", True),  # free holds on several lanes: nothing on any lane in [-9, -3]
        ])

    def test_safety(self):
        self.check("E", [
            ("!exists c: (c != E and <re{c} and re{E}>)", True),
            ("forall c: (c = E or !<re{c} and re{E}>)", True),
            ("exists c: <cl{c}>", False),
        ])

    def test_length_of_the_view(self):
        self.check("E", [("l >= 18 and l <= 18", True), ("l > 18", False)])


class TestVerticalRoad(UMLSLSemanticsTestCase):
    """
    Vertical road with u1 (northbound, x in [0, 1]) and d1 (southbound, x in [-1, 0]).
      U on u1, rear y=0, v=2 -> RE(U) = y in [0, 2]
      D on d1, rear y=3, v=2 -> RE(D) = y in [1, 3]
    d1 is on U's left, and u1 is on D's left.
    """
    roads = [road("V", "VERTICAL", 0, 1, 1)]
    cars = [car("U", "V", 0, 0, 2), car("D", "V", -1, 3, 2)]

    def test_vertical_chop_is_relative_to_the_driving_direction(self):
        self.check("U", [("<vchop{re{D}}{re{U}}>", True), ("<vchop{re{U}}{re{D}}>", False)])
        self.check("D", [("<vchop{re{U}}{re{D}}>", True), ("<vchop{re{D}}{re{U}}>", False)])


class TestLaneChangeClaims(UMLSLSemanticsTestCase):
    """
    Horizontal road with the eastbound lanes r1, r2, r3 from north to south.
      E on r1, rear x=0, v=2, changing to r2 -> RE(E) = r1 [0, 2], CL(E) = r2 [0, 2]
      A on r3, rear x=0, v=2, changing to r2 -> RE(A) = r3 [0, 2], CL(A) = r2 [0, 2]
    V(E) has the lanes r1 and r2 only (r3 is two lanes away), but A's claim overlaps it, so A is one of
    the cars of V(E), and both cars claim the same space.
    """
    roads = [road("R1", "HORIZONTAL", 0, 3, 0)]
    cars = [car("E", "R1", 0, 0, 2, transition=-0.5), car("A", "R1", 2, 0, 2, transition=0.5)]

    def test_claims(self):
        self.check("E", [
            ("<cl{E} and cl{A}>", True),
            # the potential collision check of the lane-change controller
            ("exists c: (c != E and <cl{E} and (re{c} or cl{c})>)", True),
        ])

    def test_quantifiers_range_over_the_cars_of_the_view_in_every_observed_space(self):
        self.check("E", [
            ("<exists c: cl{c}>", True),  # on r2 [0, 2], E claims
            ("<forall c: re{c}>", False),  # A reserves nothing inside V(E), so no space is reserved by all
        ])


class TestEnvelopeEndingBeforeACrossing(UMLSLSemanticsTestCase):
    """
    Horizontal road with lanes l1 (westbound), r1 and r2 (eastbound) from north to south, crossed at x=10 by a
    vertical road (d1 x in [9, 10], u1 [10, 11]).
      C on r2, rear x=-6.9, v=3, changing to r1 -> RE(C) = r2 x in [-6.9, -3.65], CL(C) = r1 x in [-6.9, -3.65]
      E on r2, rear x=4, v=0                    -> RE(E) = x in [4, 5]; V(E) has r1, r2 and X = x in [-5, 13]
    C's envelope ends 12.65 before the crossing. Its end, rounded, minus its start is not exactly 3.25, and the
    rounding error left over must not be taken for envelope reaching into the crossing.
    """
    roads = [road("R1", "HORIZONTAL", 0, 2, 1), road("R2", "VERTICAL", 10, 1, 1)]
    cars = [car("C", "R1", 1, -6.9, 3, transition=0.5), car("E", "R1", 1, 4, 0)]

    def test_reservation_does_not_reach_the_crossing(self):
        self.check("E", [
            ("<re{C} and cs>", False),
            ("<hchop{re{C}}{free and l > 7.6}{re{E}}>", True),  # r2 is free in [-3.65, 4]
            ("<cl{C}>", True),  # a car claims the adjacent lane only while its reservation is on a single segment
        ])


class TestCrossingEdges(UMLSLSemanticsTestCase):
    """
    Horizontal road (r1, l1) crossed by a vertical road at x=10 (d1, u1): the crossing is x in [9, 11].
      E on r1, rear x=7, v=2  -> RE(E) = x in [7, 9]: ends exactly where the crossing begins
      C on l1, rear x=13, v=2 -> RE(C) = x in [11, 13]: (westbound) ends exactly at the crossing's east edge
    """
    roads = [road("R1", "HORIZONTAL", 0, 1, 1), road("R2", "VERTICAL", 10, 1, 1)]
    cars = [car("E", "R1", 0, 7, 2), car("C", "R1", -1, 13, 2)]

    def test_crossing(self):
        self.check("E", [
            ("<cs and l >= 2 and l <= 2>", True),  # the crossing is 2 long on each lane
            ("<cs and l > 2>", False),
            ("<hchop{!cs}{cs}>", True),
        ])

    def test_chop_exactly_at_the_border_of_a_segment(self):
        self.check("E", [
            ("<hchop{re{E}}{cs}>", True),  # split at x=9: [7, 9] is E's, [9, 9 + d] is crossing
            ("<hchop{cs}{re{C}}>", True),  # on l1, split at x=11: crossing, then C's [11, 13]
        ])


class TestFreeOnNoLane(UMLSLSemanticsTestCase):
    """Three eastbound lanes, E alone on the northern one, its leftmost: RE(E) = [0, 2]."""
    roads = [road("R1", "HORIZONTAL", 0, 3, 0)]
    cars = [car("E", "R1", 0, 0, 2)]

    def test_free_on_a_space_without_lanes(self):
        # the upper part may span no lane, and a space without lanes is free
        self.check("E", [("vchop{free}{<re{E}>}", True)])


class TestTurnAtAWideCrossing(UMLSLSemanticsTestCase):
    """
    Horizontal road (r1, l1) crossed at x=10 by a vertical road with two lanes per direction: d2 x in [8, 9],
    d1 [9, 10] (southbound), u1 [10, 11], u2 [11, 12] (northbound).
      E on r1, rear x=5, v=4, turning right into d1: its envelope [5, 10] reaches the crossing, so E reserves
        r1 up to x=8, the crossing segments (r1, d2) and (r1, d1), and d1 for its length: y in [-2, -1].
      Y on d1, rear y=-1.5, v=0 -> RE(Y) = y in [-2.5, -1.5].
    RE(E) and RE(Y) overlap on d1 in y in [-2, -1.5]. E's lane in its view follows E's own path into d1.
    """
    roads = [road("R1", "HORIZONTAL", 0, 1, 1), road("R2", "VERTICAL", 10, 2, 2)]
    cars = [car("E", "R1", 0, 5, 4, turn=("RIGHT", "R2", -1)), car("Y", "R2", -1, -1.5, 0)]

    def test_collision_on_ego_path(self):
        safe = "!exists c: (c != E and <re{c} and re{E}>)"
        self.assertFalse(self.holds("E", safe))
        self.assertFalse(self.holds("E", safe, ego_lane_only=True))

    def test_a_formula_and_its_negation_never_both_hold(self):
        self.check("E", [("<re{Y}>", True), ("!<re{Y}>", False)])


class TestTurnIntoANarrowerRoad(UMLSLSemanticsTestCase):
    """
    Horizontal road with lanes r2, r1 (eastbound) and l1, l2 (westbound) from south to north, crossed at x=10
    by a vertical road with only d1 (x in [9, 10]) and u1 (x in [10, 11]); the crossing is y in [-2, 2].
      A on l2, rear x=13, v=2, turning left into d1.
      Z on d1, rear y=-3, v=0 -> RE(Z) = y in [-4, -3], 1 to 2 past the crossing.
    l1, on A's left, can only turn into d1 as well, so both lanes of V(A) end on d1: A's own lane after five
    crossing segments, l1 after four. Z's reservation lies on both lanes, one unit further on A's.
    """
    roads = [road("R1", "HORIZONTAL", 0, 2, 2), road("R2", "VERTICAL", 10, 1, 1)]
    cars = [car("A", "R1", -2, 13, 2, turn=("LEFT", "R2", -1)), car("Z", "R2", -1, -3, 0)]

    def test_a_segment_shared_by_two_lanes(self):
        self.check("A", [
            ("<vchop{re{Z}}{true}>", True),    # on l1's lane
            ("<vchop{true}{re{Z}}>", True),    # on A's own lane
            ("<vchop{re{Z}}{re{Z}}>", False),  # at positions that only share a point
        ])


class TestTurnedCar(UMLSLSemanticsTestCase):
    """
    Horizontal road (r1, l1) crossed at x=10 by a vertical road (d1 x in [9, 10], u1 [10, 11]).
      B on u1, rear y=-5, v=4, turning right into r1: its envelope y in [-5, 0] ends in the crossing segment
        (r1, u1), so B reserves u1 up to y=-1, (r1, u1) at x in [10, 11], and r1 for its length: x in [11, 12].
      W on l1 (westbound), rear x=w, v=2; its view covers x in [w - 9, w + 9], cut at the crossing behind it.
    """
    roads = [road("R1", "HORIZONTAL", 0, 1, 1), road("R2", "VERTICAL", 10, 1, 1)]

    @classmethod
    def setUpClass(cls):
        def snapshot(w):
            return build_snapshot(cls.roads, [car("W", "R1", -1, w, 2), car("B", "R2", 0, -5, 4, turn=("RIGHT", "R1", 0))])
        cls.near, cls.far = snapshot(20), snapshot(62)

    def test_reservation_after_the_turn(self):
        # W's view is x in [9, 29]: on r1, B reserves x in [10, 12], of which [11, 12] off the crossing
        self.check("W", [("<re{B} and !cs>", True), ("<re{B} and l >= 2>", True)], snapshot=self.near)

    def test_no_reservation_where_the_car_is_not(self):
        # W's view is x in [53, 70], far from anything B reserves
        self.check("W", [("<re{B}>", False)], snapshot=self.far)


class TestLaneEndingBeforeTheView(UMLSLSemanticsTestCase):
    """
    Horizontal road (r1, l1) crossed at x=10 by a vertical road (d1, u1). E on r1, rear x=4, v=2, turning right
    into d1. N on u1, rear y=-5, v=2 -> RE(N) = y in [-5, -3]. V(E) has two lanes: E's path, and l1's path,
    which runs (in E's direction) l1 -> (l1, d1) -> (l1, u1) -> (r1, u1) -> u1 southwards past N's reservation,
    near the end of the view, where E's shorter lane has already ended.
    """
    roads = [road("R1", "HORIZONTAL", 0, 1, 1), road("R2", "VERTICAL", 10, 1, 1)]
    cars = [car("E", "R1", 0, 4, 2, turn=("RIGHT", "R2", -1)), car("N", "R2", 0, -5, 2)]

    def test_atoms_need_a_single_lane_also_where_a_lane_has_ended(self):
        # the right part of the chop still spans both lanes
        self.check("E", [("hchop{true}{re{N}}", False), ("<re{N}>", True)])


class TestLengthComparisons(UMLSLSemanticsTestCase):
    """A single lane with E on it. 0.3 is not exact in binary, so the split at b + 0.3 is not either."""
    roads = [road("R1", "HORIZONTAL", 0, 1, 0)]
    cars = [car("E", "R1", 0, 0, 2)]

    def test_comparisons_agree_with_each_other(self):
        self.check("E", [
            ("hchop{l >= 0.3 and l <= 0.3}{true}", True),
            ("hchop{!(l < 0.3) and !(l > 0.3)}{true}", True),
            ("hchop{l < 0.3 and l >= 0.3}{true}", False),
            ("hchop{l > 0.3 and l <= 0.3}{true}", False),
        ])


if __name__ == "__main__":
    unittest.main()
