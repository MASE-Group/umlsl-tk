"""
The world extent: where the lanes end.

Settings throughout: maximal deceleration 2 and maximal speed 6, so the view horizon is H = 6^2 / (2 * 2) = 9. A car
of length 1 with its rear at p, driving east at speed 2, sees [p - 9, p + 9] along its road and reserves
[p, p + 1 + 2^2 / 4] = [p, p + 2].
"""
import unittest
from unittest import mock

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.environment.environment_creation import EnvironmentCreation
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType
from umlsl_edit.query.evaluator import UMLSLEvaluator

H = 9.0


def road(name, orientation, position, forward_lanes=1, backward_lanes=1):
    return {"uid": name, "name": name, "orientation": orientation, "position": float(position),
            "number_of_forward_lanes": forward_lanes, "number_of_backward_lanes": backward_lanes}


def car(name, road_name, position, speed=2.0, lane_index=0):
    return {"uid": name, "name": name, "road_uid": road_name, "lane_index": lane_index,
            "position_on_lane": float(position), "transition": 0.0, "speed": float(speed), "length": 1.0,
            "color": "#ff0000", "acceleration": 0.0, "next_turn": None}


def build(payload: dict) -> TrafficSnapshotModel:
    settings = SettingsModel(braking_acceleration=2.0, max_speed=6.0)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    TrafficSnapshotModel.from_dict(payload, snapshot, snapshot, settings)
    return snapshot


def west_end(snapshot) -> float:
    return -snapshot.get_world_extent()[0]


def world_view(snapshot, name) -> tuple[float, float]:
    """A car's view along an eastbound lane with no crossing, in world coordinates."""
    horizon = snapshot.get_car_by_name(name).environment.horizon
    return west_end(snapshot) + horizon.start, west_end(snapshot) + horizon.end


class TestFittedExtent(unittest.TestCase):
    def test_an_empty_world_is_the_horizon_around_the_origin(self):
        snapshot = build({"roads": [], "cars": []})
        self.assertEqual(snapshot.get_world_extent(), (H, H))

    def test_a_road_reaches_across_itself_and_its_lanes_span_the_horizon(self):
        # y in [-2, 1]: the world reaches H beyond its far edge, at y = -2
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0, 2, 1)], "cars": []})
        self.assertEqual(snapshot.get_world_extent(), (H, 2 + H))

    def test_lanes_end_the_horizon_beyond_the_farthest_view(self):
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": [car("A", "h", 100.0)]})
        # A sees [91, 109]; the lane ends H beyond that
        self.assertEqual(world_view(snapshot, "A"), (91.0, 109.0))
        self.assertEqual(snapshot.get_world_extent()[0], 109 + H)

    def test_the_extent_is_a_whole_number_of_lanes(self):
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": [car("A", "h", 100.25)]})
        self.assertEqual(snapshot.get_world_extent()[0], 119.0)  # ceil(109.25 + 9)

    def test_a_view_is_never_cut_short_by_the_end_of_its_lane(self):
        # Built one car at a time, each car first lands near (or beyond) the end of the world as it is.
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": []})
        for i, position in enumerate((15.0, 40.0, 300.0)):
            snapshot.add_car(_car_entity(snapshot, f"C{i}", position))
            self.assertEqual(world_view(snapshot, f"C{i}"), (position - H, position + H))

    def test_removing_the_farthest_car_shrinks_the_world(self):
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0)],
                          "cars": [car("A", "h", 0.0), car("B", "h", 100.0)]})
        self.assertEqual(snapshot.get_world_extent()[0], 109 + H)
        snapshot.remove_car("B")
        self.assertEqual(snapshot.get_world_extent()[0], 9 + H)
        self.assertEqual(world_view(snapshot, "A"), (-9.0, 9.0))

    def test_a_higher_maximum_speed_widens_the_views_and_the_world(self):
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": [car("A", "h", 0.0)]})
        events = []
        snapshot.attach(lambda event, data=None: events.append((event, data)))
        snapshot.settings_model.set_max_speed(8.0)  # H = 16
        self.assertEqual(world_view(snapshot, "A"), (-16.0, 16.0))
        self.assertEqual(snapshot.get_world_extent(), (32.0, 17.0))
        self.assertIn((TrafficSnapshotEventType.WORLD_EXTENT_CHANGED, (32.0, 17.0)), events)

    def test_a_vertical_road_far_east_moves_the_east_end(self):
        snapshot = build({"roads": [road("h", "HORIZONTAL", 0), road("v", "VERTICAL", 60.0)], "cars": []})
        # v covers x in [59, 61]
        self.assertEqual(snapshot.get_world_extent()[0], 61 + H)

    def test_the_extent_does_not_change_what_a_formula_means(self):
        cars = [car("A", "h", 0.0), car("B", "h", 5.0)]
        near = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": cars})
        far = build({"roads": [road("h", "HORIZONTAL", 0)], "cars": cars + [car("Z", "h", 400.0)]})
        self.assertGreater(far.get_world_extent()[0], near.get_world_extent()[0])
        for formula in ("<re{B}>", "<hchop{re{A}}{hchop{free}{re{B}}}>", "<free and l > 3>", "<l >= 18>"):
            with self.subTest(formula):
                results = [UMLSLEvaluator(s).parse_ast(formula, s.get_car_by_name("A")).evaluate(False)
                           for s in (near, far)]
                self.assertEqual(results[0], results[1])


def _car_entity(snapshot, name, position):
    from umlsl_edit.model.entities.car import Car, CarParams
    from umlsl_edit.model.traffic_value_objects.lane import Lane

    params = CarParams(name=name, lane=Lane(lane_index=0, road_uid="h"), color="#ff0000", position_on_lane=position,
                       transition=0.0, speed=2.0, length=1.0, next_turn=None, acceleration=0.0)
    snapshot.validate_car_params(params, True)
    return Car.from_params(params, snapshot, snapshot.settings_model)


class TestLoading(unittest.TestCase):
    PAYLOAD = {"roads": [road("h", "HORIZONTAL", 0), road("v", "VERTICAL", 4.0)],
               "cars": [car("A", "h", -20.0), car("B", "h", 30.0), car("C", "h", 60.0)]}

    def test_a_saved_snapshot_costs_no_environment_for_its_extent(self):
        saved = build(self.PAYLOAD).to_dict()
        with mock.patch.object(EnvironmentCreation, "build", autospec=True,
                               side_effect=EnvironmentCreation.build) as built:
            loaded = build(saved)
        # Car.from_params builds a car's environment and adding the car revalidates it; fitting the stored
        # extent again rebuilds none of them
        self.assertEqual(built.call_count, 2 * len(self.PAYLOAD["cars"]))
        self.assertEqual(loaded.get_world_extent(), tuple(saved["world_extent"]))

    def test_a_payload_without_an_extent_gets_the_same_one(self):
        self.assertEqual(build(self.PAYLOAD).get_world_extent(),
                         build(build(self.PAYLOAD).to_dict()).get_world_extent())

    def test_a_stale_stored_extent_is_fitted_again(self):
        stale = dict(build(self.PAYLOAD).to_dict(), world_extent=[500.0, 500.0])
        self.assertEqual(build(stale).get_world_extent(), build(self.PAYLOAD).get_world_extent())


class TestSimulatorCanvas(unittest.TestCase):
    """A snapshot imported from UMLSL-Sim keeps its canvas while every road and car body fits inside it."""

    CANVAS = [20.0, 12.0]

    def imported(self, cars):
        return build({"roads": [road("h", "HORIZONTAL", 0)], "cars": cars,
                      "simulator_canvas": self.CANVAS, "world_extent": self.CANVAS})

    def test_the_canvas_is_kept_and_a_view_is_cut_at_its_edge(self):
        snapshot = self.imported([car("A", "h", 15.0)])
        self.assertEqual(snapshot.get_world_extent(), (20.0, 12.0))
        self.assertEqual(world_view(snapshot, "A"), (6.0, 20.0))  # cut at the canvas edge, as in UMLSL-Sim

    def test_a_car_beyond_the_canvas_gives_the_view_and_horizon_back(self):
        snapshot = self.imported([car("A", "h", 15.0)])
        snapshot.update_car_with_params(snapshot.get_car_by_name("A").uid, _params("A", 30.0))
        self.assertEqual(world_view(snapshot, "A"), (21.0, 39.0))
        self.assertEqual(snapshot.get_world_extent(), (39 + H, 12.0))  # never smaller than the canvas

    def test_moving_back_inside_returns_to_the_canvas(self):
        snapshot = self.imported([car("A", "h", 15.0)])
        uid = snapshot.get_car_by_name("A").uid
        snapshot.update_car_with_params(uid, _params("A", 30.0))
        snapshot.update_car_with_params(uid, _params("A", 15.0))
        self.assertEqual(snapshot.get_world_extent(), (20.0, 12.0))

    def test_the_canvas_survives_saving_and_loading(self):
        saved = self.imported([car("A", "h", 15.0)]).to_dict()
        self.assertEqual(saved["simulator_canvas"], self.CANVAS)
        self.assertEqual(build(saved).get_world_extent(), (20.0, 12.0))


def _params(name, position):
    from umlsl_edit.model.entities.car import CarParams
    from umlsl_edit.model.traffic_value_objects.lane import Lane

    return CarParams(name=name, lane=Lane(lane_index=0, road_uid="h"), color="#ff0000", position_on_lane=position,
                     transition=0.0, speed=2.0, length=1.0, next_turn=None, acceleration=0.0)


if __name__ == "__main__":
    unittest.main()
