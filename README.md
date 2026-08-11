# UMLSL-TK — A Toolkit for Urban Multi-Lane Spatial Logic

UMLSL-TK bundles two complementary tools built on the traffic model and logic of
Urban Multi-Lane Spatial Logic (UMLSL):

| Tool | Purpose |
| :--- | :--- |
| **[UMLSL-Edit](UMLSL-Edit/)** | A visual editor for constructing traffic snapshots (roads, intersections, cars) and evaluating UMLSL formulae over them with its model checker. |
| **[UMLSL-Sim](UMLSL-Sim/)** | A discrete-time traffic simulator with a Gymnasium environment for training and observing reinforcement-learning agents. |

The two tools exchange scenarios through a shared JSON interchange format:
snapshots built and formally checked in UMLSL-Edit are exported to UMLSL-Sim for
simulation, and any simulation state can be sent back to UMLSL-Edit for formal
re-analysis. This closes the loop between formal specification and
simulation-based validation.

```
┌──────────────── UMLSL-Edit ────────────────┐
│  Scenario Editor  ──────►  Model Checker   │
└─┬─────────────────────▲────────────────────┘
  │ verified scenario   │ simulation snapshot
┌─▼─────────────────────┴────────────────────┐
│  Simulation  ◄─────────►  RL Training      │
└──────────────── UMLSL-Sim ─────────────────┘
```

## Requirements

* Python 3.11 or newer
* A desktop environment (both tools are graphical: UMLSL-Edit uses Qt/PySide6,
  UMLSL-Sim uses pyglet/OpenGL)

## Installation

The `install.sh` script sets up a virtual environment and installs whichever
parts of the toolkit you need.

```bash
./install.sh            # interactive menu
```

Or select the target directly:

| Command | Installs |
| :--- | :--- |
| `./install.sh all` | UMLSL-Edit **and** UMLSL-Sim including the RL stack |
| `./install.sh edit` | UMLSL-Edit only |
| `./install.sh sim` | UMLSL-Sim only, without reinforcement learning |
| `./install.sh sim-rl` | UMLSL-Sim only, with reinforcement learning |

Options:

```
--venv PATH   Virtual environment to create/use (default: .env)
--no-venv     Install into the currently active Python environment
-h, --help    Show usage
```

Then activate the environment:

```bash
source .env/bin/activate
```

The RL variants additionally pull in Gymnasium, Stable-Baselines3, Optuna and
PyTorch, so they take considerably longer to install and need several GB of
disk space. Choose `sim` if you only want to run and inspect simulations —
UMLSL-Sim starts normally without the RL packages and simply reports that the
RL modes are unavailable.

<details>
<summary>Manual installation</summary>

```bash
python3 -m venv .env
source .env/bin/activate

# UMLSL-Edit
pip install -e UMLSL-Edit

# UMLSL-Sim (choose one)
pip install -e UMLSL-Sim          # without RL
pip install -e 'UMLSL-Sim[rl]'    # with RL
```

Both tools use a `src/` layout and must be installed to be importable.
Install them **in editable mode** (`-e`): UMLSL-Sim resolves its scenario
directory relative to the package source, so a non-editable install would read
scenarios from `site-packages` rather than from this working tree, and would not
see the scenarios you export from UMLSL-Edit.

</details>

## Running UMLSL-Edit

Both tools are run as Python modules and work from any directory, but they must
be installed first (see [Installation](#installation)) and their environment
activated:

```bash
source .env/bin/activate
python -m umlsl_edit.main
```

To open a snapshot directly, pass its path:

```bash
python -m umlsl_edit.main UMLSL-Edit/sample_scenes/two_crossings_predefined.json
```

Sample snapshots are in [UMLSL-Edit/sample_scenes/](UMLSL-Edit/sample_scenes/).
`File ▸ Open` and the command line accept both the editor's native format and
the UMLSL-Sim interchange format — the format is detected from the file itself.
(`two_crossings_predefined.json` is an interchange-format sample; the other
three are native.)

**Navigation.** Drag with the left mouse button or use the arrow keys to pan;
zoom with the mouse wheel or the `+`/`-` buttons. Add and edit entities from the
left panel; `Settings` and `File` (`Load`, `Save`, `Save As`, `Export`, `Import`)
live in the top-left menu.

| Action | Shortcut |
| :--- | :--- |
| Add Car | `C` |
| Add Road | `R` |
| Add Query | `Q` |
| Edit Selected | `E` |
| Delete Selected | `Backspace` |

## Running UMLSL-Sim

### Interactive control GUI (recommended)

```bash
python -m umlsl_sim.run_control_gui
```

The control panel lets you pick a scenario and the number of NPC cars, start,
pause and rerun the simulation, configure the RL mode, algorithm, observation
model and reward, and save a paused run as a new scenario.

### Scripted use

`umlsl_sim.main` exposes the same functionality as a function call, for
batch experiments and headless runs:

```python
from umlsl_sim.main import main
from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.gui.render_mode import RenderMode

scenario = load_scenario("TWO_CROSSINGS")
main(**scenario, render_mode=RenderMode.GUI, show_reservation=True)
```

`load_scenario` takes the scenario key case-insensitively and reads
`UMLSL-Sim/src/umlsl_sim/scenarios/<key-in-lowercase>.json`. Use
`render_mode=RenderMode.NO_GUI` for headless runs. The full parameter reference,
the RL modes, and the layout of the `rl_results/` output tree are documented in
[UMLSL-Sim/README.md](UMLSL-Sim/README.md).

---

## Exchanging scenarios between the two tools

Each tool has its own native format, plus a shared **interchange format** used in
both directions:

| | Native format | Interchange format |
| :--- | :--- | :--- |
| **UMLSL-Edit** | `meta`, `roads`, `cars`, `queries` — includes UMLSL queries; used by `File ▸ Save` | written by `File ▸ Export to UMLSL-Sim`, read by `File ▸ Import from UMLSL-Sim` |
| **UMLSL-Sim** | — | `name`, `scenario_name`, `players`, `roads`, `cars` — every file in `UMLSL-Sim/src/umlsl_sim/scenarios/` |

The interchange format is exactly UMLSL-Sim's scenario format, so no conversion
step is needed on the simulator side.

### UMLSL-Edit ➜ UMLSL-Sim

1. Build and check your snapshot in UMLSL-Edit.
2. Choose **File ▸ Export to UMLSL-Sim**.
3. In the save dialog, navigate to **`UMLSL-Sim/src/umlsl_sim/scenarios/`** and save the
   file there.

   The **file name becomes the scenario key**: exporting as `my_scenario.json`
   produces `"scenario_name": "my_scenario"` and `"name": "MY_SCENARIO"` in the
   file. Use lowercase names without spaces — `load_scenario()` lowercases the
   key it is given and looks for `<key>.json`.
4. Start UMLSL-Sim. The scenario appears in the **Scenario** dropdown of the
   control GUI, or load it in a script with `load_scenario("my_scenario")`.

   If the control GUI was already running when you exported, restart it — the
   dropdown is only rescanned when the GUI itself saves a scenario.

Saving anywhere else works too; just move or copy the file into
`UMLSL-Sim/src/umlsl_sim/scenarios/` afterwards, since that directory is the only place
UMLSL-Sim looks for scenarios.

**What is carried over.** All roads and cars, with their lanes, positions,
speeds, colors and turn intentions; the exported `players` count equals the
number of cars, so UMLSL-Sim reproduces exactly the cars you edited and adds no
random traffic. All cars are exported as type `NPC`.

**What is not.** UMLSL queries are *not* part of the interchange format. Keep a
native `File ▸ Save` copy of any snapshot whose queries you want to preserve —
exporting alone will lose them.

### UMLSL-Sim ➜ UMLSL-Edit

1. Run a simulation, then pause it at the state you want to analyse
   (**Play / Pause**).
2. Type a name into **New scenario name** and press **Save paused scenario**.
   The file is written to `UMLSL-Sim/src/umlsl_sim/scenarios/<name>.json`; the status log
   reports the path, how many cars were written, and whether any mid-crossing
   car had to be snapped back to the entry of its next lane segment.
3. In UMLSL-Edit choose **File ▸ Import from UMLSL-Sim** and open that file.
   (**File ▸ Open** works too — the interchange format is detected
   automatically.)
4. Add UMLSL queries and evaluate them against the imported snapshot.

An imported scenario has no native file associated with it, so **Save** asks you
to **Save As** first. This is deliberate: it prevents the editor from writing
native JSON — which UMLSL-Sim cannot read — over a working simulator scenario.

Any scenario shipped with UMLSL-Sim can be imported the same way, which is a
convenient starting point:

```
UMLSL-Edit  ▸  File ▸ Import from UMLSL-Sim
            ▸  UMLSL-Sim/src/umlsl_sim/scenarios/two_crossings_predefined.json
```

### Representation differences handled by the conversion

The two tools model the world differently; the conversion is not a plain copy,
and understanding it explains small coordinate shifts you may notice:

| | UMLSL-Edit | UMLSL-Sim |
| :--- | :--- | :--- |
| Unit size | 1 unit = 1 | 1 unit = 40 |
| Origin | centre of the canvas | bottom-left corner |
| Canvas | unbounded, view is panned | fixed 40 × 24 lanes |
| Lane indexing | signed, `-n … -1 \| 0 … n` around the road axis | two groups counted outward, `right` and `left` |
| Maximum speed | one global setting | one value per car |
| Turning | explicit turn intention | implicit, via the car's goal |

Because UMLSL-Sim's canvas is bounded, exporting a snapshot that contains no
road named `bottom`, `top`, `left` or `right` adds those four border roads
automatically, and coordinates are rebased between the two origins. Round trips
are therefore faithful in structure but not byte-identical.

## Repository layout

Both tools follow the same `src/` layout, and each package is named after the
tool it implements.

```
UMLSL-Edit/                       the editor and model checker
  src/umlsl_edit/
    main.py                       application entry point
    commands/                     undoable user actions
    controllers/                  application, command, data and event control
    model/                        entities, domain models, errors, geometry
    query/                        UMLSL query parser and AST
    services/                     native and interchange persistence
    view/                         Qt widgets, dialogs and traffic canvas
  sample_scenes/                  example snapshots
  tests/                          unit and integration tests

UMLSL-Sim/                        the simulator and RL environment
  src/umlsl_sim/
    main.py                       scripted entry point
    run_control_gui.py            interactive control GUI
    run_scenario.py               run one scenario without RL
    run_manual_drive.py           drive a car manually
    simulation/                   traffic environment, controllers, factories
    car_control/                  per-car A* and safety controllers
    gui/                          pyglet rendering and control panel
    reinforcement_learning/       Gymnasium env, algorithms, rewards
    scenario_io/                  scenario loader and car specifications
    scenarios/                    scenario files — the export/import target
  manual_tests/                   long-running RL training checks

install.sh                        dependency installer
```

## Troubleshooting

**`No module named 'umlsl_edit'` (or `'umlsl_sim'`).** The package is not
installed in the interpreter you are using. Both tools use a `src/` layout, so
they are not importable straight from the working directory — installing them is
what puts them on the import path. Run `./install.sh` and activate the
environment it reports, or install directly:

```bash
pip install -e UMLSL-Edit
pip install -e UMLSL-Sim
```

If you upgraded from an older checkout, remove the package under its previous
name first: `pip uninstall mlsl-simulation`.

**UMLSL-Sim finds no scenarios.** The package was installed without `-e`. See
[Installation](#installation).

## Citing

If you use UMLSL-TK in academic work, please cite the accompanying tool paper
and the UMLSL foundations it builds on.
