"""Command line of the control GUI launcher (the window itself needs a display)."""
import unittest
from unittest.mock import patch

from umlsl_sim.app import run_control_gui


class TestRunControlGui(unittest.TestCase):
    def test_defaults_open_the_gui_without_a_scenario(self):
        with patch("umlsl_sim.gui.control.launch") as launch:
            run_control_gui.run([])
        launch.assert_called_once_with(scenario=None, autorun=False)

    def test_scenario_and_run_are_passed_on(self):
        with patch("umlsl_sim.gui.control.launch") as launch:
            run_control_gui.run(["--scenario", "My_Scenario", "--run"])
        launch.assert_called_once_with(scenario="My_Scenario", autorun=True)

    def test_run_needs_a_scenario(self):
        with patch("umlsl_sim.gui.control.launch") as launch, \
                patch("sys.stderr"), self.assertRaises(SystemExit):
            run_control_gui.run(["--run"])
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
