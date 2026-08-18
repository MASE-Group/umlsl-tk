"""RL helpers for the control GUI: capability gating, saved-run discovery and a
background worker for the long-running headless RL modes (train / optimize).

Two independent capability flags, because they fail for different reasons:

* ``ENUMS_AVAILABLE`` — whether the RL option enums could be imported at all.
  Each enum lives in its own light module, and its package populates the
  registry on first lookup rather than on import, so naming the dropdown
  options costs nothing.
* ``RUNTIME_AVAILABLE`` — whether the ML stack is installed, so an RL job that
  needs it is refused with a clear message rather than crashing mid-training.

Neither flag imports gymnasium, stable-baselines3 or torch. This module is
imported to open the window, and a plain NPC run must not pay seconds of import
for an ML stack it never calls; the real import happens when an RL job starts.
"""
from __future__ import annotations

import logging
import os
import queue
import threading
from importlib import util
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

# --- enum discovery (always available) -----------------------------------
try:
    from umlsl_sim.rl.modes import RLMode
    from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
    from umlsl_sim.rl.observations.observation_model_types import (
        ObservationModelType,
    )
    from umlsl_sim.rl.rewards.reward_types import RewardType

    ENUMS_AVAILABLE = True
except Exception as exc:  # pragma: no cover - defensive
    RLMode = RLAlgorithmType = ObservationModelType = RewardType = None  # type: ignore
    ENUMS_AVAILABLE = False
    log.warning("RL enums unavailable: %s", exc)


# --- runtime availability -------------------------------------------------
#: What an RL job needs on top of the base install (the ``[rl]`` extra).
_RUNTIME_PACKAGES = ("gymnasium", "stable_baselines3")


def runtime_availability() -> Tuple[bool, str]:
    """(available, reason). ``available`` is True if the ML stack is installed.

    Located with `find_spec` rather than imported: importing stable_baselines3
    drags torch in behind it, seconds of work charged to opening a window that
    may never run an RL job. A package that is absent — the case this gates — is
    found either way. One that is installed but broken raises when the job
    imports it for real, and `RLWorker` reports that where it happens.
    """
    missing = [name for name in _RUNTIME_PACKAGES if util.find_spec(name) is None]
    if not missing:
        return True, ""
    return False, (
        "RL extras not installed. Install them with:  pip install -e \".[rl]\"  "
        f"(missing: {', '.join(missing)})"
    )


RUNTIME_AVAILABLE, RUNTIME_REASON = runtime_availability()


# --- dropdown option helpers ---------------------------------------------
# Human-facing RL mode labels mapped to RLMode enum members.
MODE_OFF = "Off (plain NPCs)"


def rl_mode_labels() -> List[str]:
    if not ENUMS_AVAILABLE:
        return [MODE_OFF]
    return [
        MODE_OFF,
        "Load trained model",
        "Train",
        "Optimize hyperparameters",
        "Optimize + train",
    ]


_LABEL_TO_MODE = {
    "Load trained model": "LOAD_TRAINED_MODEL",
    "Train": "TRAIN",
    "Optimize hyperparameters": "OPTIMIZE",
    "Optimize + train": "OPTIMIZE_AND_TRAIN",
    "Load history": "LOAD_HISTORY",
}


def mode_from_label(label: str):
    """Return the RLMode enum member for a label, or None for 'Off'."""
    if label == MODE_OFF or not ENUMS_AVAILABLE:
        return None
    name = _LABEL_TO_MODE.get(label)
    return RLMode[name] if name else None


def algorithm_names() -> List[str]:
    return [m.name for m in RLAlgorithmType] if ENUMS_AVAILABLE else []


# How each algorithm handles unsafe actions. The choice of algorithm *is* the
# choice of safety mechanism, so the GUI spells it out rather than leaving the
# user to infer it from the enum name.
_ALGORITHM_DESCRIPTIONS = {
    "PPO": "PPO: unsafe actions stay available; safety comes from the reward.",
    "MASKABLE_PPO": (
        "MASKABLE_PPO: safety shield on — the safety controller masks unsafe "
        "actions before the agent acts."
    ),
}


def algorithm_description(name: str) -> str:
    """One-line explanation of what an algorithm choice means for safety."""
    return _ALGORITHM_DESCRIPTIONS.get(name, "")


def observation_names() -> List[str]:
    return [m.name for m in ObservationModelType] if ENUMS_AVAILABLE else []


def reward_names() -> List[str]:
    return [m.name for m in RewardType] if ENUMS_AVAILABLE else []


def _models_base() -> Optional[Path]:
    """Root of the saved-model tree, or None if the path cannot be resolved.

    Reuses the constant `rl.rl_io` itself loads from rather than rebuilding the
    path, so what the GUI lists stays in step with what the controller actually
    loads. It is read from `rl.paths`, which carries it without rl_io's pandas
    and ML imports — those are an ``[rl]`` extra, and on a plain install the
    listing helpers should degrade to "no models" rather than raising.
    """
    try:
        from umlsl_sim.rl import paths
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Model directory unavailable: %s", exc)
        return None

    return Path(paths.RESULT_MODEL_PATH)


def list_model_ids(scenario_name: str, algo: str, obs: str, reward: str) -> List[str]:
    """Directory names (timestamps) of saved models for the given config."""
    root = _models_base()
    if root is None:
        return []
    base = root / scenario_name / algo / obs / reward
    if not base.is_dir():
        return []
    ids = [p.name for p in base.iterdir() if p.is_dir()]
    ids.sort(reverse=True)
    return ids


def list_history_files(scenario_name: str, algo: str, obs: str, reward: str, id_model: str) -> List[str]:
    root = _models_base()
    if root is None:
        return []
    base = root / scenario_name / algo / obs / reward / id_model / "history"
    if not base.is_dir():
        return []
    files = [p.name for p in base.iterdir() if p.suffix == ".pkl"]
    files.sort(reverse=True)
    return files


# --- background worker for train / optimize -------------------------------
class RLWorker:
    """Runs a headless RLRunner mode on a daemon thread and reports
    lifecycle messages through a thread-safe queue polled by the GUI."""

    def __init__(self) -> None:
        self.queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(
        self,
        roads,
        players: int,
        predefined_cars,
        scenario_name: str,
        rl_mode,
        rl_algorithm_type,
        observation_model_type,
        reward_type,
        id_model: Optional[str] = None,
        id_hyperparams: Optional[str] = None,
        id_history: Optional[str] = None,
    ) -> bool:
        if self.running:
            self.queue.put(("warn", "An RL job is already running."))
            return False
        if not RUNTIME_AVAILABLE:
            self.queue.put(("error", RUNTIME_REASON))
            return False

        def _run() -> None:
            self.queue.put(("info", f"Starting RL job: {rl_mode.name} on '{scenario_name}'."))
            self.queue.put(("info", "Detailed progress is printed to the terminal."))
            try:
                from umlsl_sim.rl.training.rl_runner import RLRunner
                from umlsl_sim.config.render_mode import RenderMode

                controller = RLRunner(
                    roads=roads,
                    players=players,
                    render_mode=RenderMode.NO_GUI,
                    show_reservation=False,
                    scenario_name=scenario_name,
                    rl_mode=rl_mode,
                    rl_algorithm_type=rl_algorithm_type,
                    observation_model_type=observation_model_type,
                    reward_type=reward_type,
                    id_model=id_model,
                    id_history=id_history,
                    id_hyperparams=id_hyperparams,
                    predefined_cars=predefined_cars,
                )
                controller.run()
            except Exception as exc:  # noqa: BLE001
                log.exception("RL job failed")
                self.queue.put(("error", f"RL job failed: {exc}"))
                self.queue.put(("done", ""))
                return

            model_id = os.path.basename(getattr(controller, "model_path", "") or "")
            hyper_id = os.path.basename(getattr(controller, "hyperparams_path", "") or "")
            if rl_mode.name in ("TRAIN", "OPTIMIZE_AND_TRAIN"):
                self.queue.put((
                    "info",
                    f"Training finished. Model id: {model_id}. "
                    "Load it via RL Mode -> 'Load trained model'.",
                ))
            elif rl_mode.name == "OPTIMIZE":
                self.queue.put((
                    "info",
                    f"Optimization finished. Hyperparameters id: {hyper_id}.",
                ))
            else:
                self.queue.put(("info", f"RL job '{rl_mode.name}' finished."))
            self.queue.put(("done", ""))

        self._thread = threading.Thread(target=_run, name="rl-worker", daemon=True)
        self._thread.start()
        return True

    def drain(self) -> List[Tuple[str, str]]:
        """Return and clear all pending messages (call from the GUI thread)."""
        out: List[Tuple[str, str]] = []
        while True:
            try:
                out.append(self.queue.get_nowait())
            except queue.Empty:
                break
        return out
