"""Locating UMLSL-Sim and starting its control GUI."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from umlsl_edit.services import simulator_launcher
from umlsl_edit.services.simulator_launcher import (
    SimulatorNotInstalledError,
    SimulatorProcess,
    launch_simulator,
    scenario_key,
    scenarios_dir,
)


class TestScenarioKey(unittest.TestCase):
    def test_keys_are_lower_case_and_safe(self):
        self.assertEqual(scenario_key("My Demo-Scene (v2)!"), "my_demo_scene_v2")
        self.assertEqual(scenario_key("  two__crossings  "), "two_crossings")
        self.assertEqual(scenario_key("already_fine_1"), "already_fine_1")

    def test_names_without_letters_or_digits_give_no_key(self):
        self.assertEqual(scenario_key(" -- "), "")


class TestScenariosDir(unittest.TestCase):
    def test_finds_the_scenario_folder_of_the_installed_package(self):
        with tempfile.TemporaryDirectory() as package:
            folder = Path(package) / "scenario" / "scenarios"
            folder.mkdir(parents=True)
            spec = SimpleNamespace(submodule_search_locations=[package])
            with patch.object(simulator_launcher.importlib.util, "find_spec", return_value=spec):
                self.assertEqual(scenarios_dir(), folder)

    def test_reports_a_missing_installation(self):
        with patch.object(simulator_launcher.importlib.util, "find_spec", return_value=None):
            with self.assertRaises(SimulatorNotInstalledError) as raised:
                scenarios_dir()
        self.assertIn("pip install -e UMLSL-Sim", str(raised.exception))


class TestLaunch(unittest.TestCase):
    def test_starts_the_control_gui_on_the_scenario_with_this_interpreter(self):
        with patch.object(simulator_launcher.subprocess, "Popen") as popen:
            simulator = launch_simulator("my_demo")
        try:
            args = popen.call_args.args[0]
            self.assertEqual(args, [sys.executable, "-m", "umlsl_sim.app.run_control_gui",
                                    "--scenario", "my_demo", "--run"])
            self.assertIs(popen.call_args.kwargs["stderr"], subprocess.STDOUT)
            self.assertTrue(simulator.log_path.name.startswith("umlsl-sim-my_demo-"))
        finally:
            simulator.log_path.unlink(missing_ok=True)

    def test_failure_is_reported_only_after_an_error_exit(self):
        with tempfile.NamedTemporaryFile("w", suffix=".log", delete=False) as log:
            log.write("starting\nTraceback ...\nValueError: boom\n")
        process = MagicMock()
        simulator = SimulatorProcess(process=process, log_path=Path(log.name))
        try:
            process.poll.return_value = None
            self.assertIsNone(simulator.failure())
            process.poll.return_value = 0
            self.assertIsNone(simulator.failure())
            process.poll.return_value = 1
            failure = simulator.failure()
            self.assertIn("exited with code 1", failure)
            self.assertIn("ValueError: boom", failure)
        finally:
            Path(log.name).unlink()


if __name__ == "__main__":
    unittest.main()
