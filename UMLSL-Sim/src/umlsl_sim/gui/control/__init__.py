"""Interactive pyglet control GUI for the MLSL traffic simulation.

This package hosts a single-window GUI that embeds the existing pyglet
simulation renderer next to a control panel. It lets the user pick a scenario
and RL options from dropdowns, start / pause / rerun simulations, launch RL
optimization / training / model-based simulation, and save a paused scenario
as a new predefined-car scenario JSON.

Entry point: ``python -m umlsl_sim.run_control_gui`` (or, equivalently,
``python -m umlsl_sim.gui.control``).
"""

from umlsl_sim.gui.control.app import launch

__all__ = ["launch"]
