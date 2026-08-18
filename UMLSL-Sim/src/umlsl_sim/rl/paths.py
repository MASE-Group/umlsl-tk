"""Where RL results live on disk.

Split out of `rl_io` so that asking *where* a result would be -- which is all
the control GUI does to list the saved models for a configuration -- does not
drag in pandas, gymnasium and torch behind `rl_io`'s own imports. `rl_io`
re-exports these names, so the reader and the writer still agree on one
definition.

Anchored to the package, not the CWD: these paths are used for both saving and
loading, so a CWD-relative value would silently file results under whichever
directory training happened to run from, and later reads would look somewhere
else. Mirrors `scenario.loader._DATA_DIR`, which anchors the scenario JSONs the
same way.
"""
from __future__ import annotations

from pathlib import Path

RESULTS_ROOT = Path(__file__).resolve().parent.parent / "rl_results"

RESULT_MODEL_PATH = str(RESULTS_ROOT / "models")
RESULT_PARAM_PATH = str(RESULTS_ROOT / "hyperparameters")
