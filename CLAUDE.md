# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

UMLSL-TK is a monorepo of two independent Python packages (Python ≥ 3.11) for Urban Multi-Lane Spatial Logic. They share no code and have no import dependency on each other. They talk only through a JSON file format and by launching each other as subprocesses.

- **UMLSL-Edit** (`UMLSL-Edit/src/umlsl_edit`): a PySide6 editor for traffic snapshots, plus a model checker for UMLSL formulae.
- **UMLSL-Sim** (`UMLSL-Sim/src/umlsl_sim`): a pyglet discrete-time traffic simulator, plus a Gymnasium/Stable-Baselines3 RL stack (the optional `[rl]` extra).

`slides/` is a separate Slidev deck for a conference talk (npm; see `slides/README.md`). It is untracked and is not part of the toolkit.

## Setup and commands

Both packages use a `src/` layout and **must be installed editable**. UMLSL-Sim resolves `scenario/scenarios/` and `rl_results/` relative to its package source. A non-editable install reads from `site-packages` and does not see scenarios that UMLSL-Edit exports into the working tree.

```bash
./install.sh all            # both tools, Sim with [rl], plus [dev] (pytest); venv at ./.env
./install.sh edit|sim|sim-rl   # subsets; --venv PATH, --no-venv, --no-dev
source .env/bin/activate
# manual: pip install -e 'UMLSL-Edit[dev]'  and  pip install -e 'UMLSL-Sim[dev]'  (or '[rl,dev]')
```

Run:

```bash
python -m umlsl_edit.main [snapshot.json]              # native or interchange format, auto-detected
python -m umlsl_sim.app.run_control_gui [--scenario KEY --run]
python -m umlsl_sim.app.run_scenario --scenario circuit --players 12   # --help for RL/headless options
```

Tests. Run each suite **from its own package directory**. Both test dirs are packages named `tests` and import `tests.helpers` / `tests.test_...`, so they cannot be collected together from the repo root.

```bash
cd UMLSL-Edit && pytest tests
cd UMLSL-Edit && pytest tests/test_query_semantics.py::SomeTestCase::test_name

cd UMLSL-Sim && pytest                       # testpaths = ["tests"]; base install only
cd UMLSL-Sim && pytest tests/integration -q  # whole episodes on every bundled scenario
cd UMLSL-Sim && pytest manual_tests/ -v      # needs [rl]; SB3 smoke tests, kept out of the default run
```

There is no configured linter or formatter.

Benchmarks (the numbers in the paper; committed results live in `*/benchmarks/results/`): `UMLSL-Edit/benchmarks/formula_timing.py` + `summarise.py`, and `UMLSL-Sim/benchmarks/{episode_outcomes,throughput,summarise}.py`. Run them from inside their `benchmarks/` directory. Each has its own README.

## UMLSL-Edit architecture

`ApplicationController` (`controllers/application_controller.py`) is the composition root. It builds the models and wires three sub-controllers:

- **Models** (`model/domain_models/`): `TrafficSnapshotModel` (cars and roads, composed from mixins), `SettingsModel` (global braking acceleration and **one global max speed**), and `UMLSLQueriesModel`. Each is an *Observable*: a plain-Python observer pattern, deliberately not Qt signals, so the model has no Qt dependency. Other code reads and writes the snapshot through the `TrafficSnapshotReader` / `TrafficSnapshotWriter` interfaces.
- **CommandController**: every mutation goes through a `Command` object (`commands/{cars,roads,umlsl,settings,persistence}/`, base class in `commands/command.py`). The controller runs validation and preflight first, then executes the command. It also tracks "changed since last save". Undo/redo is stubbed out (commented code), not implemented.
- **EventController**: subscribes to the model observables and forwards each event to a `ViewEventHandler` (`controllers/view_event_contract.py`). The view implements that contract in `view/view_event_handler_impl.py`.
- **DataController**: read-only queries for the view.

Loading a different file replaces the models wholesale through `ApplicationController.replace_snapshot`, which re-points every controller.

**View** (`view/`): Qt widgets, QML list views, and the `QGraphicsScene` traffic canvas. `view/widgets/compiled_widgets/ui_main.py` is **generated** from `view/widgets/qt_widgets/main.ui` by `pyside6-uic`. Edit the `.ui` file, regenerate, and commit both. Never hand-edit the generated file.

**Model checker** (`query/`): `Lexer` → `ASTParser` (`query/ast/`, one node type per UMLSL construct: chop, claim, reserve, free, somewhere, quantifiers, …) → evaluation. `UMLSLEvaluator` is the API. The GUI evaluates each query in a **separate process** (`query/evaluation_worker.py`). The worker rebuilds the models from a serialized snapshot dict and the settings, so anything an evaluation needs must survive `to_dict`/`from_dict`. Quantifiers range over the cars whose reservation or claim overlaps the ego car's view (`model/environment/`).

**Services** (`services/`): native persistence; the interchange format (`external_persistence_service.py`, which handles Sim → Edit import plus the fix-ups that make a Sim scenario valid in the editor); `simulator_scenario.py` (Edit → Sim translation and the "is this simulatable" checks); and the cross-process launchers described below.

## UMLSL-Sim architecture

A strict layer stack: a module imports only modules below it. `UMLSL-Sim/README.md` ("Module Layout") is authoritative. In short:

`app/` (entry points; the composition root, and the only module that knows all the others) → `runners/` → `gui/` | `rl/` → `control/` → `scenario/`, `factories/` → `simulation/` → `config/`, `palettes/`.

- `simulation/` must not import GUI, RL, or a concrete controller. It is driven through two `typing.Protocol` seams in `simulation/ports.py`: `CarController` (NPC driver; the default A* controller is named only inside a function, as a lazy default) and `Renderer` (`NullRenderer` for headless runs, `PygletRenderer` bound by importing `umlsl_sim.app`). Keep runners free of `if gui:` branches, and keep training free of any pyglet import.
- `rl/` has four swappable parts (`algorithms`, `hyperparameters`, `observations`, `rewards`). The registries are filled by decorators such as `@register_reward_model(RewardType.X)`. They are populated **lazily** on the first `get_*` lookup (`rl/plugin_loader.py`), so importing an enum does not pull in torch or gymnasium. To add a variant, create a new module and an enum member. No consumer needs editing.
- Lane changes use a claim → withdraw/commit reservation protocol (`simulation/` reservations; see the Sim README section "Lane Changes"). Safety comes either from `control/safety` through an action shield (MaskablePPO) or from the safety-aware reward (PPO).
- Scenarios are JSON files in `src/umlsl_sim/scenario/scenarios/`. `load_scenario(key)` lowercases the key and reads `<key>.json`.

## Editor ↔ Simulator hand-off

- **Interchange format** = UMLSL-Sim's scenario format (`name`, `scenario_name`, `players`, `roads`, optional `cars`; cars may carry `next_lane`). UMLSL queries are *not* carried over.
- The two coordinate systems differ: Edit uses 1 unit per lane with the origin at the canvas centre and a signed lane index; Sim uses 40 px per lane on a fixed 40 × 24-lane torus with the origin at the bottom-left. Export adds border roads along empty canvas edges. Import removes them again when no car uses them. Round trips (Edit→Sim→Edit and Sim→Edit→Sim) are expected to be lossless. The mapping is documented at the top of `services/simulator_scenario.py` and in the root README.
- **Edit → Sim**: `services/simulator_launcher.py` locates `umlsl_sim` with `importlib.util.find_spec` (without importing it). It writes the scenario into Sim's scenarios folder and starts `python -m umlsl_sim.app.run_control_gui --scenario KEY --run` with the same interpreter.
- **Sim → Edit**: `gui/control/editor_launcher.py` starts `python -m umlsl_edit.main --import-from-sim FILE`. `services/editor_instance.py` implements single-instance forwarding: if an editor already listens on the Qt local socket, the new process sends it one JSON line `{"import_from_sim": PATH}`, receives `ok`, and exits.
- The tools never import each other. Keep it that way: each one runs in its own process, so each can be installed without the other.
