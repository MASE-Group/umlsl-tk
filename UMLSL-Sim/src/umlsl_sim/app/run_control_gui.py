"""Launcher for the interactive UMLSL-Sim control GUI.

Run as a module:

    python -m umlsl_sim.app.run_control_gui
    python -m umlsl_sim.app.run_control_gui --scenario my_scenario --run

The GUI embeds the simulation next to a control panel and lets you pick a
scenario and RL options, start / pause / rerun runs, launch RL
optimization / training / model-based simulation, and save a paused run as a new
predefined-car scenario. It reuses the same building blocks as ``main.py``.

``--scenario`` preselects a scenario in the dropdown, and ``--run`` starts a
plain simulation of it straight away. UMLSL-Edit's "Simulate in UMLSL-Sim"
menu item opens the GUI this way after exporting the current snapshot.

The "RL algorithm / safety mechanism" dropdown selects how unsafe actions are
handled: ``PPO`` leaves that to the reward (pair it with
``SAFETY_AWARE_REWARD``), while ``MASKABLE_PPO`` turns on the safety shield,
masking unsafe actions out before the agent acts. Saved models are filed under
the algorithm name, so the "Saved model" list only offers models trained with
the mechanism currently selected.
"""
import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m umlsl_sim.app.run_control_gui",
        description="Open the interactive UMLSL-Sim control GUI.",
    )
    parser.add_argument(
        "--scenario", default=None, metavar="NAME",
        help="scenario to preselect (a file stem in scenario/scenarios/, case-insensitive)",
    )
    parser.add_argument(
        "--run", action="store_true",
        help="start a plain simulation of --scenario as soon as the window opens",
    )
    return parser


def run(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.run and args.scenario is None:
        parser.error("--run needs --scenario")

    # Imported after parsing so that --help works without opening a display.
    from umlsl_sim.gui.control import launch

    launch(scenario=args.scenario, autorun=args.run)


if __name__ == "__main__":
    run()
