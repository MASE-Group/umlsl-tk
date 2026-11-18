"""
Find the installed UMLSL-Sim and open its control GUI on a scenario.

UMLSL-Sim reads scenarios only from its own package folder
(``umlsl_sim/scenario/scenarios``), so that is where the editor exports to. The
package is located with ``importlib.util.find_spec``, which does not import it:
the simulator always runs in its own process, started with this interpreter.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SIMULATOR_PACKAGE = "umlsl_sim"
CONTROL_GUI_MODULE = "umlsl_sim.app.run_control_gui"


class SimulatorNotInstalledError(RuntimeError):
    """UMLSL-Sim is not importable from the editor's Python environment."""


def scenarios_dir() -> Path:
    """
    The folder UMLSL-Sim loads its scenarios from.

    Raises:
        SimulatorNotInstalledError: If UMLSL-Sim is not installed in this environment.
    """
    spec = importlib.util.find_spec(SIMULATOR_PACKAGE)
    if spec is None or not spec.submodule_search_locations:
        raise SimulatorNotInstalledError(
            "UMLSL-Sim is not installed in this Python environment.\n\n"
            "Install it next to UMLSL-Edit, for example with\n"
            "./install.sh all  or  pip install -e UMLSL-Sim"
        )
    folder = Path(next(iter(spec.submodule_search_locations))) / "scenario" / "scenarios"
    if not folder.is_dir():
        raise SimulatorNotInstalledError(f"UMLSL-Sim has no scenario folder at\n{folder}")
    return folder


def scenario_key(text: str) -> str:
    """
    A scenario key UMLSL-Sim can load: lower case, letters, digits and ``_``.

    ``load_scenario`` lower-cases the key it is given and opens ``<key>.json``,
    so anything else in a name would make the scenario unreachable.
    """
    key = re.sub(r"[^a-z0-9_]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", key).strip("_")


@dataclass
class SimulatorProcess:
    """A running UMLSL-Sim, with the file its output is written to."""

    process: subprocess.Popen
    log_path: Path

    def failure(self, max_lines: int = 8) -> str | None:
        """
        Why the simulator stopped, if it has already exited with an error.

        Returns:
            The exit code and the end of its output, or ``None`` while it is
            still running or after it closed normally.
        """
        code = self.process.poll()
        if code is None or code == 0:
            return None
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        except OSError:
            lines = []
        tail = "\n".join(lines[-max_lines:])
        return f"UMLSL-Sim exited with code {code}.\n\n{tail}\n\nFull output: {self.log_path}"


def launch_simulator(key: str) -> SimulatorProcess:
    """
    Open the UMLSL-Sim control GUI and start simulating scenario ``key``.

    The simulator runs detached in its own session, so it stays open when the
    editor closes. Its output goes to a log file rather than the editor's
    terminal.

    Raises:
        OSError: If the process cannot be started.
    """
    with tempfile.NamedTemporaryFile(
            prefix=f"umlsl-sim-{key}-", suffix=".log", delete=False
    ) as log:
        if os.name == "posix":
            detach = {"start_new_session": True}
        else:
            detach = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        process = subprocess.Popen(
            [sys.executable, "-m", CONTROL_GUI_MODULE, "--scenario", key, "--run"],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            **detach,
        )
    return SimulatorProcess(process=process, log_path=Path(log.name))
