"""Find the installed UMLSL-Edit and open a saved scenario in it.

The counterpart of UMLSL-Edit's ``simulator_launcher``. The editor is located
with ``importlib.util.find_spec``, which does not import it (it needs Qt), and
always runs in its own process, started with this interpreter.

The editor is started with ``--import-from-sim FILE``. If an UMLSL-Edit window
is already open, the new process hands FILE to that window and exits. The open
window then asks whether to save its unsaved changes before it imports FILE.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

EDITOR_PACKAGE = "umlsl_edit"
EDITOR_MODULE = "umlsl_edit.main"
IMPORT_FROM_SIM_FLAG = "--import-from-sim"


class EditorNotInstalledError(RuntimeError):
    """UMLSL-Edit is not importable from the simulator's Python environment."""


def check_editor_installed() -> None:
    """
    Raises:
        EditorNotInstalledError: If UMLSL-Edit is not installed in this environment.
    """
    if importlib.util.find_spec(EDITOR_PACKAGE) is None:
        raise EditorNotInstalledError(
            "UMLSL-Edit is not installed in this Python environment. "
            "Install it next to UMLSL-Sim, for example with "
            "./install.sh all  or  pip install -e UMLSL-Edit"
        )


@dataclass
class EditorProcess:
    """A started UMLSL-Edit, with the file its output is written to."""

    process: subprocess.Popen
    log_path: Path

    def failure(self, max_lines: int = 8) -> Optional[str]:
        """Why the editor stopped, if it has already exited with an error.

        Returns:
            The exit code and the end of its output, or ``None`` while it is
            still running, or after it closed normally (which is also what it
            does after it handed the file to an editor that was already open).
        """
        code = self.process.poll()
        if code is None or code == 0:
            return None
        try:
            lines = self.log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        except OSError:
            lines = []
        tail = " | ".join(lines[-max_lines:])
        return f"UMLSL-Edit exited with code {code}: {tail} (full output: {self.log_path})"


def open_in_editor(scenario_path: Path) -> EditorProcess:
    """Open ``scenario_path`` in UMLSL-Edit, or in the UMLSL-Edit window already open.

    The editor runs detached in its own session, so it stays open when the
    simulator closes. Its output goes to a log file.

    Raises:
        EditorNotInstalledError: If UMLSL-Edit is not installed.
        OSError: If the process cannot be started.
    """
    check_editor_installed()
    with tempfile.NamedTemporaryFile(
            prefix=f"umlsl-edit-{scenario_path.stem}-", suffix=".log", delete=False
    ) as log:
        if os.name == "posix":
            detach = {"start_new_session": True}
        else:
            detach = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        process = subprocess.Popen(
            [sys.executable, "-m", EDITOR_MODULE, IMPORT_FROM_SIM_FLAG, str(scenario_path.resolve())],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            **detach,
        )
    return EditorProcess(process=process, log_path=Path(log.name))
