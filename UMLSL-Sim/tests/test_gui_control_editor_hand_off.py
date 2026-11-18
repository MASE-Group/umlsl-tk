"""Saving a paused run for UMLSL-Edit and starting the editor on it (the window needs a display)."""
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from umlsl_sim.factories.car_spec import CarSpec, PositionRef, resolve_position
from umlsl_sim.gui.control import editor_launcher
from umlsl_sim.gui.control.editor_launcher import (
    EditorNotInstalledError,
    EditorProcess,
    open_in_editor,
)
from umlsl_sim.gui.control.scenario_saver import save_current_scenario, unique_stem
from umlsl_sim.scenario.loader import load_scenario
from umlsl_sim.simulation.traffic_environment import TrafficEnv


def paused_run(key="two_crossings", steps=137, seed=1) -> TrafficEnv:
    random.seed(seed)
    scenario = load_scenario(key)
    env = TrafficEnv(roads=scenario["roads"], players=scenario["players"],
                     predefined_cars=scenario["predefined_cars"])
    for _ in range(steps):
        env.play_step()
    return env


class TestUniqueNames(unittest.TestCase):
    def test_a_free_name_is_kept_and_a_taken_one_numbered(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            self.assertEqual(unique_stem("demo", out), "demo")
            (out / "demo.json").write_text("{}")
            (out / "demo_2.json").write_text("{}")
            self.assertEqual(unique_stem("demo", out), "demo_3")

    def test_unique_save_never_fails_on_a_taken_name(self):
        env = paused_run(steps=10)
        with tempfile.TemporaryDirectory() as folder:
            first = save_current_scenario(env, "Demo", out_dir=Path(folder), unique=True)
            second = save_current_scenario(env, "Demo", out_dir=Path(folder), unique=True)
            self.assertEqual((first.path.name, second.path.name), ("demo.json", "demo_2.json"))
            with self.assertRaises(FileExistsError):
                save_current_scenario(env, "Demo", out_dir=Path(folder))


class TestNextLane(unittest.TestCase):
    """Each saved car says which lane it enters after its next crossing."""

    def save(self, env):
        with tempfile.TemporaryDirectory() as folder:
            path = save_current_scenario(env, "paused", out_dir=Path(folder)).path
            return json.loads(path.read_text())

    def test_next_lane_is_a_lane_segment_of_the_scenario(self):
        env = paused_run()
        data = self.save(env)
        self.assertTrue(all("next_lane" in c for c in data["cars"]))
        for car in data["cars"]:
            with self.subTest(car["name"]):
                resolve_position(env.roads, PositionRef.from_dict(car["next_lane"]))
        self.assertTrue(any(c["next_lane"]["road"] != c["start"]["road"] for c in data["cars"]))

    def test_next_lane_lies_past_the_crossing_ahead(self):
        env = paused_run()
        for car in self.save(env)["cars"]:
            start, _ = resolve_position(env.roads, PositionRef.from_dict(car["start"]))
            target, _ = resolve_position(env.roads, PositionRef.from_dict(car["next_lane"]))
            with self.subTest(car["name"]):
                self.assertIsNot(start, target)
                self.assertIsNotNone(start.end_crossing)

    def test_the_simulator_ignores_next_lane(self):
        data = self.save(paused_run())
        specs = [CarSpec.from_dict(c) for c in data["cars"]]
        env = TrafficEnv(roads=paused_run(steps=0).roads, players=data["players"], predefined_cars=specs)
        env.play_step()
        self.assertEqual(len(env.cars), len(specs))


class TestEditorLauncher(unittest.TestCase):
    def test_reports_a_missing_editor(self):
        with patch.object(editor_launcher.importlib.util, "find_spec", return_value=None):
            with self.assertRaises(EditorNotInstalledError):
                open_in_editor(Path("x.json"))

    def test_starts_the_editor_detached_on_the_file(self):
        with patch.object(editor_launcher.importlib.util, "find_spec", return_value=object()), \
                patch.object(editor_launcher.subprocess, "Popen") as popen:
            editor = open_in_editor(Path("some/demo_paused.json"))
        command = popen.call_args.args[0]
        self.assertEqual(command[:4], [sys.executable, "-m", "umlsl_edit.main", "--import-from-sim"])
        self.assertEqual(Path(command[4]), Path("some/demo_paused.json").resolve())
        self.assertIs(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
        editor.log_path.unlink()

    def test_failure_is_only_reported_for_an_error_exit(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as log:
            log.write("Traceback\nImportError: no Qt\n")
        process = MagicMock()
        editor = EditorProcess(process=process, log_path=Path(log.name))
        for code in (None, 0):
            process.poll.return_value = code
            self.assertIsNone(editor.failure())
        process.poll.return_value = 1
        self.assertIn("ImportError: no Qt", editor.failure())
        Path(log.name).unlink()


if __name__ == "__main__":
    unittest.main()
