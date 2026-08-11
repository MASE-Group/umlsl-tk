"""Launcher for the interactive UMLSL-Sim control GUI.

Run as a module:

    python -m umlsl_sim.run_control_gui

The GUI embeds the simulation next to a control panel and lets you pick a
scenario and RL options, start / pause / rerun runs, launch RL
optimization / training / model-based simulation, and save a paused run as a new
predefined-car scenario. It reuses the same building blocks as ``main.py``.
"""
from umlsl_sim.gui.control import launch

if __name__ == "__main__":
    launch()
