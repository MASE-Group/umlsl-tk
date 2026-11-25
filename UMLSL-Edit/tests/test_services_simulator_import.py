"""Translation of UMLSL-Sim scenarios back into editor snapshots: the inverse of the export."""
import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.services.external_persistence_service import ExternalPersistenceService
from umlsl_edit.services.simulator_scenario import (
    build_simulator_scenario,
    map_road,
    unmap_road,
)
from tests.test_services_simulator_scenario import CROSSING, SAMPLE_SCENES, car, load_native, road, turn


def import_payload(payload, max_speed=15):
    """``payload`` read like File > Import does: the snapshot, the notes and the settings."""
    settings = SettingsModel(braking_acceleration=8.0, max_speed=max_speed)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    notes = ExternalPersistenceService.deserialize(json.loads(json.dumps(payload)), snapshot, snapshot, settings)
    return snapshot.to_dict(), notes, settings


def export(roads, cars):
    scenario = build_simulator_scenario({"roads": roads, "cars": cars}, "demo", 15)
    assert scenario.can_run, scenario.errors
    return scenario.payload


def named(data):
    """Roads and cars by name, with each turn's target road named instead of by uid."""
    road_name = {r["uid"]: r["name"] for r in data["roads"]}
    roads = {r["name"]: r for r in data["roads"]}
    cars = {}
    for c in data["cars"]:
        t = c["next_turn"]
        cars[c["name"]] = dict(c, road=road_name[c["road_uid"]], turn=t and (
            t["direction"], road_name[t["target_lane"]["road_uid"]], t["target_lane"]["lane_index"]))
    return roads, cars


def ref(road_name, direction, lane, position):
    return {"road": road_name, "direction": direction, "lane": lane, "position": position}


class TestRoadMapping(unittest.TestCase):
    def test_unmap_road_inverts_map_road(self):
        for orientation in ("HORIZONTAL", "VERTICAL"):
            for forward, backward in ((2, 1), (1, 3), (0, 2), (3, 0)):
                with self.subTest(orientation=orientation, forward=forward, backward=backward):
                    original = road("r", orientation, -3.0, forward, backward)
                    back = unmap_road(map_road(original))
                    self.assertEqual(back, {k: original[k] for k in back})


class TestTurnsFromGoals(unittest.TestCase):
    """The export puts a turning car's goal past the crossing; the import reads the turn back."""

    def test_left_and_right_turns_survive_the_round_trip(self):
        cars = [car("A", "H", 0, -8.0, next_turn=turn("LEFT", "V", 0)),
                car("B", "H", 1, -8.0, next_turn=turn("RIGHT", "V", -2)),
                car("C", "H", -1, 8.0, next_turn=turn("LEFT", "V", -1)),
                car("D", "V", -1, 6.0, next_turn=turn("RIGHT", "H", -1))]
        _, imported = named(import_payload(export(CROSSING, cars))[0])
        self.assertEqual(imported["A"]["turn"], ("LEFT", "V", 0))
        self.assertEqual(imported["B"]["turn"], ("RIGHT", "V", -2))
        self.assertEqual(imported["C"]["turn"], ("LEFT", "V", -1))
        self.assertEqual(imported["D"]["turn"], ("RIGHT", "H", -1))

    def test_straight_on_stays_without_a_turn(self):
        _, imported = named(import_payload(export(CROSSING, [car("A", "H", 0, -8.0)]))[0])
        self.assertIsNone(imported["A"]["turn"])

    def test_a_far_goal_is_straight_on(self):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        # On V northbound, but south of H: reached only after more crossings.
        payload["cars"][0]["first_goal"] = ref("V", "left", 0, 200)
        data, notes, _ = import_payload(payload)
        self.assertIsNone(named(data)[1]["A"]["turn"])
        self.assertEqual(notes, [])  # random goals far away are normal, not worth a note


class TestTurnsFromThePlannedRoute(unittest.TestCase):
    """UMLSL-Sim writes ``next_lane``: the lane after the next crossing on the car's route."""

    def payload(self):
        return export(CROSSING, [car("A", "H", 0, -8.0)])

    def test_next_lane_wins_over_the_goal(self):
        payload = self.payload()
        payload["cars"][0]["next_lane"] = ref("V", "left", 0, 720)
        self.assertEqual(named(import_payload(payload)[0])[1]["A"]["turn"], ("LEFT", "V", 0))

    def test_next_lane_straight_on_ignores_a_turning_goal(self):
        payload = self.payload()
        payload["cars"][0]["first_goal"] = ref("V", "left", 0, 720)
        payload["cars"][0]["next_lane"] = dict(payload["cars"][0]["start"], position=1280)
        self.assertIsNone(named(import_payload(payload)[0])[1]["A"]["turn"])

    def test_a_move_the_editor_cannot_show_goes_straight_and_is_reported(self):
        payload = self.payload()
        payload["cars"][0]["next_lane"] = ref("H", "left", 0, 460)  # a U-turn
        data, notes, _ = import_payload(payload)
        self.assertIsNone(named(data)[1]["A"]["turn"])
        self.assertEqual(len(notes), 1)
        self.assertIn("A", notes[0])
        self.assertIn("straight on", notes[0])


class TestBorderRoads(unittest.TestCase):
    def test_unused_border_roads_are_left_out(self):
        roads, _ = named(import_payload(export(CROSSING, [car("A", "H", 0, -8.0)]))[0])
        self.assertEqual(set(roads), {"H", "V"})

    def test_editor_sim_editor_gives_back_the_original_roads(self):
        data, _, _ = import_payload(export(CROSSING, [car("A", "H", 0, -8.0)]))
        key = lambda r: (r["name"], r["orientation"], r["position"],
                         r["number_of_forward_lanes"], r["number_of_backward_lanes"])
        self.assertEqual(sorted(map(key, data["roads"])), sorted(map(key, CROSSING)))

    def test_a_border_road_with_a_car_on_it_stays(self):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        payload["cars"].append(dict(payload["cars"][0], name="B", start=ref("bottom", "right", 0, 200)))
        del payload["cars"][1]["first_goal"]
        roads, _ = named(import_payload(payload)[0])
        self.assertEqual(set(roads), {"H", "V", "bottom"})

    def test_a_border_road_a_car_turns_into_stays(self):
        payload = export(CROSSING, [car("A", "V", -1, 6.0)])
        # A drives south on V from y = 300 px towards the bottom border road and turns left (east).
        payload["cars"][0]["start"]["position"] = 300
        payload["cars"][0]["next_lane"] = ref("bottom", "right", 0, 1280)
        roads, cars = named(import_payload(payload)[0])
        self.assertIn("bottom", roads)
        self.assertEqual(cars["A"]["turn"], ("LEFT", "bottom", 0))

    def test_a_border_road_that_export_would_not_add_again_stays(self):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        top = next(r for r in payload["roads"] if r["name"] == "top")
        top.update(top=880, left=2)  # two lanes: not the road the export adds
        roads, _ = named(import_payload(payload)[0])
        self.assertIn("top", roads)

    def test_exporting_again_restores_the_border_roads(self):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        again = build_simulator_scenario(import_payload(payload)[0], "demo", 15).payload
        key = lambda r: (r["name"], r["horizontal"], r["top"], r["right"], r["left"])
        self.assertEqual(sorted(map(key, again["roads"])), sorted(map(key, payload["roads"])))


class TestEditorRules(unittest.TestCase):
    """Rules of the editor that UMLSL-Sim does not have."""

    def payload(self, **changes):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        payload["cars"][0].update(changes)
        return payload

    def test_names_with_umlsl_tokens_are_upper_cased(self):
        payload = self.payload(name="Green")
        payload["cars"].append(dict(payload["cars"][0], name="GREEN", start=ref("H", "right", 0, 200)))
        next(r for r in payload["roads"] if r["name"] == "V")["name"] = "free"
        for c in payload["cars"]:
            for key in ("start", "first_goal"):
                if c.get(key, {}).get("road") == "V":
                    c[key]["road"] = "free"
        data, notes, _ = import_payload(payload)
        roads, cars = named(data)
        self.assertEqual(set(cars), {"GREEN", "GREEN_2"})
        self.assertIn("FREE", roads)
        self.assertIn("Green → GREEN_2", notes[0])
        self.assertIn("free → FREE", notes[0])

    def test_names_without_tokens_are_kept(self):
        _, notes, _ = import_payload(self.payload(name="Maroon"))
        self.assertEqual(notes, [])

    def test_max_speed_grows_until_every_car_fits(self):
        # 15² / 16 + 1 > 15² / 16: at the maximum speed no car fits. 16 is enough.
        data, notes, settings = import_payload(self.payload(speed=15, max_speed=15))
        self.assertEqual(settings.max_speed, 16)
        self.assertEqual(data["cars"][0]["speed"], 15)
        self.assertIn("from 15 to 16", notes[0])

    def test_car_on_a_crossing_edge_moves_one_pixel_into_its_lane(self):
        # H's lane segment past V starts at x = 1000 px, which the editor counts as part of the crossing.
        data, _, _ = import_payload(self.payload(start=ref("H", "right", 1, 1000)))
        self.assertAlmostEqual(data["cars"][0]["position_on_lane"], 1001 / 40 - 20)


class TestShowcaseRoundTrip(unittest.TestCase):
    def test_editor_sim_editor_keeps_roads_cars_and_turns(self):
        for name in ("sim_demo_one_crossing", "sim_demo_asymmetric_roads"):
            with self.subTest(name):
                original = load_native(SAMPLE_SCENES / f"{name}.json")
                back, notes, _ = import_payload(build_simulator_scenario(original, name, 15).payload)
                (roads_a, cars_a), (roads_b, cars_b) = named(original), named(back)
                road_key = lambda r: (r["orientation"], r["position"],
                                      r["number_of_forward_lanes"], r["number_of_backward_lanes"])
                self.assertEqual({n: road_key(r) for n, r in roads_a.items()},
                                 {n: road_key(r) for n, r in roads_b.items()})
                for car_name, a in cars_a.items():
                    b = cars_b[car_name]
                    self.assertEqual((a["road"], a["lane_index"], a["turn"]), (b["road"], b["lane_index"], b["turn"]))
                    self.assertAlmostEqual(a["position_on_lane"], b["position_on_lane"], delta=1 / 40)
                self.assertEqual(notes, [])


@unittest.skipUnless(importlib.util.find_spec("umlsl_sim"), "UMLSL-Sim is not installed")
class TestPausedSimulatorRuns(unittest.TestCase):
    """What UMLSL-Sim's 'Open in UMLSL-Edit' saves, mid-run, opens in the editor."""

    def test_every_bundled_scenario_opens_mid_run(self):
        from umlsl_sim.gui.control.scenario_saver import save_current_scenario
        from umlsl_sim.scenario.loader import available_scenarios, load_scenario
        from umlsl_sim.simulation.traffic_environment import TrafficEnv

        turns = 0
        for key in available_scenarios():
            with self.subTest(key):
                random.seed(1)
                scenario = load_scenario(key)
                env = TrafficEnv(roads=scenario["roads"], players=scenario["players"],
                                 predefined_cars=scenario["predefined_cars"])
                for _ in range(137):
                    env.play_step()
                with tempfile.TemporaryDirectory() as folder:
                    path = save_current_scenario(env, key, out_dir=Path(folder)).path
                    payload = json.loads(path.read_text(encoding="utf-8"))
                data, _, _ = import_payload(payload)
                self.assertEqual(len(data["cars"]), len(payload["cars"]))
                turns += sum(c["next_turn"] is not None for c in data["cars"])
        self.assertGreater(turns, 0)


if __name__ == "__main__":
    unittest.main()


class TestCanvasFollowsTheWorld(unittest.TestCase):
    """The simulator canvas is the editor's world extent, and comes back as it went."""

    ROADS = [road("H", "HORIZONTAL", 0.0, 2, 1), road("V", "VERTICAL", 30.0, 1, 2),
             road("far", "HORIZONTAL", 13.0, 1, 1)]
    CARS = [car("A", "H", 0, 40.0), car("B", "far", -1, -35.0)]

    def snapshot(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        TrafficSnapshotModel.from_dict({"roads": self.ROADS, "cars": self.CARS}, snapshot, snapshot, settings)
        return snapshot

    def test_the_canvas_is_twice_the_world_extent_and_holds_everything(self):
        snapshot = self.snapshot()
        half_width, half_height = snapshot.get_world_extent()
        scenario = build_simulator_scenario(snapshot.to_dict(), "big", 15)
        self.assertEqual((scenario.payload["width"], scenario.payload["height"]),
                         (round(2 * half_width * 40), round(2 * half_height * 40)))
        # far beyond the 40 x 24 lanes of old, and nothing of it outside the canvas
        self.assertGreater(scenario.payload["width"], 40 * 40)
        self.assertEqual(scenario.issues, [])
        borders = {r["name"]: r for r in scenario.payload["roads"] if r["name"] in ("right", "top")}
        self.assertEqual(borders["right"]["top"], scenario.payload["width"] - 40)
        self.assertEqual(borders["top"]["top"], scenario.payload["height"] - 40)

    def test_edit_to_sim_to_edit_is_exact_and_keeps_the_canvas(self):
        original = self.snapshot().to_dict()
        payload = build_simulator_scenario(original, "big", 15).payload
        back, _, _ = import_payload(payload)

        roads, cars = named(back)
        for r in self.ROADS:
            mapped = roads[r["name"]]
            self.assertEqual(
                {k: mapped[k] for k in ("orientation", "position", "number_of_forward_lanes", "number_of_backward_lanes")},
                {k: r[k] for k in ("orientation", "position", "number_of_forward_lanes", "number_of_backward_lanes")},
            )
        for c in self.CARS:
            self.assertEqual((cars[c["name"]]["road"], cars[c["name"]]["lane_index"],
                              cars[c["name"]]["position_on_lane"]),
                             (c["road_uid"], c["lane_index"], c["position_on_lane"]))
        self.assertEqual(back["world_extent"], original["world_extent"])
        self.assertEqual(back["simulator_canvas"], original["world_extent"])

    def test_sim_to_edit_to_sim_keeps_the_canvas_of_the_scenario(self):
        payload = build_simulator_scenario(self.snapshot().to_dict(), "big", 15).payload
        back, _, _ = import_payload(payload)
        again = build_simulator_scenario(back, "big", 15).payload
        self.assertEqual((again["width"], again["height"]), (payload["width"], payload["height"]))
        key = lambda r: (r["name"], r["horizontal"], r["top"], r["right"], r["left"])
        self.assertEqual(sorted(map(key, again["roads"])), sorted(map(key, payload["roads"])))

    def test_a_scenario_that_states_no_canvas_has_the_old_one(self):
        payload = export(CROSSING, [car("A", "H", 0, -8.0)])
        for field in ("width", "height"):
            payload.pop(field)
        back, _, _ = import_payload(payload)
        self.assertEqual(back["simulator_canvas"], [20.0, 12.0])
        self.assertEqual(back["world_extent"], [20.0, 12.0])
