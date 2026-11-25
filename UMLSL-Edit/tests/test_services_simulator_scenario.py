"""Translation of editor snapshots into UMLSL-Sim scenarios, and the checks on them."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from umlsl_edit.commands.persistence.export_snapshot import (
    ExportSnapshot,
    SimulatorIncompatibleError,
)
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel
from umlsl_edit.services.external_persistence_service import ExternalPersistenceService
from umlsl_edit.services.persistence_service import PersistenceService
from umlsl_edit.services.simulator_scenario import (
    Severity,
    build_simulator_scenario,
    map_lane,
    map_road,
    unmap_lane,
)

SAMPLE_SCENES = Path(__file__).resolve().parents[1] / "sample_scenes"


def road(uid, orientation, position, forward, backward, name=None):
    return {
        "uid": uid, "name": name or uid, "orientation": orientation, "position": position,
        "number_of_forward_lanes": forward, "number_of_backward_lanes": backward,
    }


def car(name, road_uid, lane_index, position, speed=5.0, length=1.0, transition=0.0, next_turn=None):
    return {
        "uid": f"car-{name}", "name": name, "road_uid": road_uid, "lane_index": lane_index,
        "position_on_lane": position, "transition": transition, "speed": speed,
        "length": length, "color": "#112233", "acceleration": 0.0, "next_turn": next_turn,
    }


def turn(direction, road_uid, lane_index):
    return {"direction": direction, "target_lane": {"road_uid": road_uid, "lane_index": lane_index}}


CROSSING = [road("H", "HORIZONTAL", 0.0, 2, 1), road("V", "VERTICAL", 4.0, 1, 2)]
"""H: y in [-2, 1], two lanes +x below the centre. V: x in [2, 5], one lane +y east of it."""


def messages(scenario, severity=None):
    return [i.message for i in scenario.issues if severity is None or i.severity is severity]


def settings_and_snapshot():
    settings = SettingsModel(braking_acceleration=8.0, max_speed=15)
    return settings, TrafficSnapshotModel(settings_model=settings)


def load_native(path: Path) -> dict:
    """A native sample as ``to_dict`` output, after the editor model validated it."""
    data = json.loads(path.read_text(encoding="utf-8"))
    data["queries"] = []  # queries are not exported, and evaluating them needs worker processes
    settings, snapshot = settings_and_snapshot()
    PersistenceService.deserialize(data, snapshot, snapshot, settings, UMLSLQueriesModel(snapshot))
    return snapshot.to_dict()


def load_interchange(path: Path) -> dict:
    """An interchange-format file as ``to_dict`` output, read like File > Import does."""
    settings, snapshot = settings_and_snapshot()
    ExternalPersistenceService.deserialize(
        json.loads(path.read_text(encoding="utf-8")), snapshot, snapshot, settings)
    return snapshot.to_dict()


class TestRoadAndLaneMapping(unittest.TestCase):
    def test_horizontal_road_keeps_forward_lanes_on_the_right(self):
        sim = map_road(CROSSING[0])
        # centre line y = 0 is 12 lanes up; the low edge is two forward lanes below it
        self.assertEqual((sim.horizontal, sim.top, sim.right, sim.left), (True, 400, 2, 1))

    def test_asymmetric_vertical_road_is_not_mirrored(self):
        sim = map_road(CROSSING[1])
        # forward lanes run +y (the simulator's "left"), backward lanes -y ("right")
        self.assertEqual((sim.horizontal, sim.top, sim.right, sim.left), (False, 880, 2, 1))

    def test_lane_mapping_is_inverted_by_unmap_lane(self):
        for spec in CROSSING:
            sim = map_road(spec)
            lanes = list(range(spec["number_of_forward_lanes"])) + \
                [-(i + 1) for i in range(spec["number_of_backward_lanes"])]
            mapped = set()
            for lane_index in lanes:
                direction, lane = map_lane(sim, lane_index)
                self.assertGreaterEqual(lane, 0)
                self.assertLess(lane, sim.right if direction == "right" else sim.left)
                self.assertEqual(unmap_lane(sim.horizontal, sim.right, direction, lane), lane_index)
                mapped.add((direction, lane))
            self.assertEqual(len(mapped), len(lanes))

    def test_lanes_next_to_the_centre_line(self):
        horizontal, vertical = map_road(CROSSING[0]), map_road(CROSSING[1])
        self.assertEqual(map_lane(horizontal, 0), ("right", 1))  # innermost right lane
        self.assertEqual(map_lane(horizontal, -1), ("left", 0))
        self.assertEqual(map_lane(vertical, 0), ("left", 0))
        self.assertEqual(map_lane(vertical, -1), ("right", 1))  # innermost right lane


class TestBorderRoads(unittest.TestCase):
    def test_missing_border_roads_are_added(self):
        payload = build_simulator_scenario({"roads": CROSSING, "cars": []}, "x").payload
        borders = {r["name"]: r for r in payload["roads"] if r["name"] not in ("H", "V")}
        self.assertEqual(set(borders), {"bottom", "top", "left", "right"})
        self.assertEqual(borders["right"]["top"], 1560)
        self.assertEqual(borders["top"]["top"], 920)

    def test_border_names_never_clash_with_user_roads(self):
        roads = [road("r1", "HORIZONTAL", 0.0, 1, 1, name="left")]
        names = [r["name"] for r in build_simulator_scenario({"roads": roads, "cars": []}, "x").payload["roads"]]
        self.assertEqual(len(names), len(set(names)))

    def test_round_trip_from_umlsl_sim_is_exact(self):
        path = SAMPLE_SCENES / "two_crossings_predefined.json"
        original = json.loads(path.read_text(encoding="utf-8"))

        exported = build_simulator_scenario(load_interchange(path), "two_crossings_predefined", 15)

        key = lambda r: (r["name"], r["horizontal"], r["top"], r["right"], r["left"])
        self.assertEqual(sorted(map(key, exported.payload["roads"])), sorted(map(key, original["roads"])))
        start = lambda c: tuple(c["start"][k] for k in ("road", "direction", "lane", "position"))
        self.assertEqual(sorted(map(start, exported.payload["cars"])), sorted(map(start, original["cars"])))
        self.assertEqual(exported.issues, [])


class TestChecks(unittest.TestCase):
    def test_empty_scenario_reports_no_roads_and_no_cars(self):
        scenario = build_simulator_scenario({"roads": [], "cars": []}, "x")
        self.assertFalse(scenario.can_run)
        errors = " ".join(messages(scenario, Severity.ERROR))
        self.assertIn("no roads", errors)
        self.assertIn("no cars", errors)

    def test_roads_without_cars_cannot_run(self):
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": []}, "x")
        self.assertEqual(messages(scenario, Severity.ERROR),
                         ["The scenario has no cars. Add at least one car to simulate."])

    def test_valid_scenario_has_no_issues(self):
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": [car("A", "H", 0, -8.0)]}, "x")
        self.assertTrue(scenario.can_run)
        self.assertEqual(scenario.issues, [])

    def test_road_outside_the_canvas(self):
        roads = CROSSING + [road("far", "HORIZONTAL", 13.0, 1, 1)]
        scenario = build_simulator_scenario({"roads": roads, "cars": [car("A", "H", 0, -8.0)]}, "x")
        self.assertEqual(len(scenario.errors), 1)
        self.assertIn("Road 'far' lies outside the UMLSL-Sim canvas", scenario.errors[0].message)

    def test_road_overlapping_a_border_road(self):
        roads = CROSSING + [road("edge", "VERTICAL", -18.5, 1, 1)]  # x in [-19.5, -17.5]
        scenario = build_simulator_scenario({"roads": roads, "cars": [car("A", "H", 0, -8.0)]}, "x")
        self.assertIn("Road 'edge' overlaps the left border road", " ".join(messages(scenario)))

    def test_overlapping_parallel_roads(self):
        roads = CROSSING + [road("H2", "HORIZONTAL", 1.5, 1, 1)]
        scenario = build_simulator_scenario({"roads": roads, "cars": [car("A", "H", 0, -8.0)]}, "x")
        self.assertIn("Roads 'H' and 'H2' overlap", " ".join(messages(scenario)))

    def test_car_outside_the_canvas(self):
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": [car("A", "H", 0, 25.0)]}, "x")
        self.assertIn("Car 'A' is outside the UMLSL-Sim canvas", " ".join(messages(scenario)))

    def test_car_inside_a_border_crossing(self):
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": [car("A", "H", 0, 19.5)]}, "x")
        self.assertIn("Car 'A' starts inside the crossing where 'H' meets the right border road",
                      " ".join(messages(scenario)))

    def test_overlapping_cars(self):
        cars = [car("A", "H", 0, -8.0), car("B", "H", 0, -7.5), car("C", "H", 1, -7.5)]
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": cars}, "x")
        self.assertEqual(messages(scenario, Severity.ERROR),
                         ["Cars 'A' and 'B' overlap. UMLSL-Sim cannot start with overlapping cars."])

    def test_cars_touching_bumpers_do_not_overlap(self):
        cars = [car("A", "H", 0, -8.0), car("B", "H", 0, -7.0)]
        self.assertTrue(build_simulator_scenario({"roads": CROSSING, "cars": cars}, "x").can_run)

    def test_reversing_car(self):
        scenario = build_simulator_scenario(
            {"roads": CROSSING, "cars": [car("A", "H", 0, -8.0, speed=-2.0)]}, "x")
        self.assertIn("Car 'A' drives backwards", " ".join(messages(scenario, Severity.ERROR)))

    def test_lane_change_in_progress_is_only_a_warning(self):
        scenario = build_simulator_scenario(
            {"roads": CROSSING, "cars": [car("A", "H", 0, -8.0, transition=0.3)]}, "x")
        self.assertTrue(scenario.can_run)
        self.assertIn("Car 'A' is changing lanes", messages(scenario, Severity.WARNING)[0])

    def test_more_cars_than_lane_segments(self):
        roads = [road("H", "HORIZONTAL", 0.0, 1, 0)]
        cars = [car(f"C{i}", "H", 0, -19.0 + 1.5 * i, length=0.5) for i in range(25)]
        scenario = build_simulator_scenario({"roads": roads, "cars": cars}, "x")
        self.assertIn("lane segments", " ".join(messages(scenario, Severity.ERROR)))


class TestCarsAndGoals(unittest.TestCase):
    def build(self, *cars, max_speed=None):
        scenario = build_simulator_scenario({"roads": CROSSING, "cars": list(cars)}, "demo", max_speed)
        return {c["name"]: c for c in scenario.payload["cars"]}

    def test_payload_header(self):
        payload = build_simulator_scenario(
            {"roads": CROSSING, "cars": [car("A", "H", 0, -8.0)]}, "My_Demo").payload
        self.assertEqual((payload["name"], payload["scenario_name"], payload["players"]), ("MY_DEMO", "my_demo", 1))

    def test_start_is_the_rear_of_the_car_in_pixels(self):
        cars = self.build(car("A", "H", 0, -8.0), car("B", "V", -2, 6.0))
        self.assertEqual(cars["A"]["start"], {"road": "H", "direction": "right", "lane": 1, "position": 480})
        self.assertEqual(cars["B"]["start"], {"road": "V", "direction": "right", "lane": 0, "position": 720})

    def test_max_speed_is_the_global_setting(self):
        cars = self.build(car("A", "H", 0, -8.0, speed=0.0), max_speed=15)
        self.assertEqual((cars["A"]["speed"], cars["A"]["max_speed"]), (0, 15))

    def test_straight_goal_is_past_the_next_crossing(self):
        cars = self.build(car("A", "H", 0, -8.0), car("B", "H", -1, 8.0))
        # A drives +x from x=480 towards V at [880, 1000]; B drives -x from 1120 back across V.
        self.assertEqual(cars["A"]["first_goal"], {"road": "H", "direction": "right", "lane": 1, "position": 1280})
        self.assertEqual(cars["B"]["first_goal"], {"road": "H", "direction": "left", "lane": 0, "position": 460})

    def test_turn_goal_is_the_target_lane_past_the_crossing(self):
        left = car("A", "H", 0, -8.0, next_turn=turn("LEFT", "V", 0))
        right = car("B", "H", 1, -8.0, next_turn=turn("RIGHT", "V", -2))
        cars = self.build(left, right)
        # H spans y in [400, 520]: north of it the first segment is [520, 920], south of it [40, 400].
        self.assertEqual(cars["A"]["first_goal"], {"road": "V", "direction": "left", "lane": 0, "position": 720})
        self.assertEqual(cars["B"]["first_goal"], {"road": "V", "direction": "right", "lane": 0, "position": 220})

    def test_untranslatable_turn_falls_back_to_a_random_goal(self):
        scenario = build_simulator_scenario(
            {"roads": CROSSING, "cars": [car("A", "H", 0, -8.0, next_turn=turn("LEFT", "H", 0))]}, "x")
        self.assertNotIn("first_goal", scenario.payload["cars"][0])
        self.assertTrue(scenario.can_run)
        self.assertIn("turn of car 'A'", messages(scenario, Severity.WARNING)[0])


class TestShowcaseScenes(unittest.TestCase):
    SIMULATABLE = ("sim_demo_one_crossing", "sim_demo_asymmetric_roads")

    def test_simulatable_showcases_have_no_issues(self):
        for name in self.SIMULATABLE:
            with self.subTest(name):
                scenario = build_simulator_scenario(load_native(SAMPLE_SCENES / f"{name}.json"), name, 15)
                self.assertEqual(scenario.issues, [])

    def test_not_simulatable_showcase_lists_every_problem(self):
        scenario = build_simulator_scenario(
            load_native(SAMPLE_SCENES / "sim_demo_not_simulatable.json"), "x", 15)
        errors = messages(scenario, Severity.ERROR)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("Car 'Backwards' drives backwards" in e for e in errors))
        self.assertTrue(any("'P' and 'Q' overlap" in e for e in errors))
        # road 'Far' (y = 13) used to lie outside the 40 x 24 canvas; the canvas now grows around it
        self.assertFalse(any("Far" in e for e in errors))

    @unittest.skipUnless(importlib.util.find_spec("umlsl_sim"), "UMLSL-Sim is not installed")
    def test_exported_scenes_run_in_umlsl_sim(self):
        from umlsl_sim.factories.car_spec import CarSpec
        from umlsl_sim.simulation.road_network.road_network import Road
        from umlsl_sim.simulation.traffic_environment import TrafficEnv

        scenes = [(n, load_native(SAMPLE_SCENES / f"{n}.json")) for n in self.SIMULATABLE]
        scenes.append(("two_crossings_predefined",
                       load_interchange(SAMPLE_SCENES / "two_crossings_predefined.json")))
        for name, data in scenes:
            with self.subTest(name):
                payload = build_simulator_scenario(data, name, 15).payload
                roads = [Road(r["name"], r["horizontal"], r["top"], r["right"], r["left"])
                         for r in payload["roads"]]
                env = TrafficEnv(roads=roads, players=payload["players"],
                                 predefined_cars=[CarSpec.from_dict(c) for c in payload["cars"]],
                                 world_size=(payload["width"], payload["height"]))
                for _ in range(200):
                    env.play_step()
                self.assertEqual(env.total_crashes, 0)


class TestExportSnapshot(unittest.TestCase):
    def test_refuses_to_write_a_scenario_umlsl_sim_cannot_run(self):
        reader = MagicMock()
        reader.to_dict.return_value = {"roads": CROSSING, "cars": []}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "demo.json")
            with self.assertRaises(SimulatorIncompatibleError) as raised:
                ExportSnapshot(path, reader, max_speed=15).execute()
            self.assertFalse(os.path.exists(path))
        self.assertIn("no cars", str(raised.exception))

    def test_writes_the_payload_named_after_the_file(self):
        reader = MagicMock()
        reader.to_dict.return_value = {"roads": CROSSING, "cars": [car("A", "H", 0, -8.0)]}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "my_demo.json")
            ExportSnapshot(path, reader, max_speed=15).execute()
            with open(path, encoding="utf-8") as file:
                payload = json.load(file)
        self.assertEqual(payload["scenario_name"], "my_demo")
        self.assertEqual(payload["cars"][0]["max_speed"], 15)


if __name__ == "__main__":
    unittest.main()
