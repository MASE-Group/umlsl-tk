# UMLSL-Edit

The scenario-editing and model-checking component of the UMLSL toolkit (UMLSL-TK):
a visual editor for building traffic snapshots (cars, roads, and intersections)
and evaluating UMLSL language queries.

## Installation

**Prerequisites:** Python 3.11+

From the toolkit root, the installer sets up a virtual environment and installs
this tool:

```bash
./install.sh edit
```

To install it by hand into an environment of your own, from this directory:

```bash
pip install -e .
```

The editable install (`-e`) is what puts `umlsl_edit` on the import path — the
package lives under `src/`, so it is not importable from the working directory
without being installed.

## Running the Program

Activate the environment the installation created, then run the application
from any directory:

```bash
source ../.env/bin/activate
python -m umlsl_edit.main
```

**Open a file directly:**
Launch the editor and load a specific traffic snapshot by passing the file path as an argument:
```bash
python -m umlsl_edit.main <path/to/snapshot_file>
```

Example snapshots ship in [sample_scenes/](sample_scenes/). Both the editor's
native format and the UMLSL-Sim interchange format are accepted — the format is
detected from the file itself. `two_crossings_predefined.json` is an
interchange-format sample; the other three are native.

## Editor Features & Navigation

* **Canvas Navigation:** Click and drag the left mouse button or use the arrow keys to pan across the canvas. Zoom using the mouse wheel or the `+`/`-` buttons.
* **Entity Management:** Use the left panel to manage your environment. Click `+` to add entities, or use the pen icon to edit/delete them.
* **Drag & Drop:** Select any car or road and drag it with the mouse to quickly reposition it.
* **Settings & Files:** Access `Settings` and `File` management (`Open`, `Save`, `Save As`, `Export to UMLSL-Sim`, `Import from UMLSL-Sim`) from the top-left menu.

Exporting writes the shared interchange format that UMLSL-Sim reads; UMLSL
queries are not part of that format, so keep a native `Save` copy of any
snapshot whose queries you want to preserve. An imported snapshot has no native
file behind it, so `Save` asks you to `Save As` first. The round trip between
the two tools is documented in the [toolkit README](../README.md#exchanging-scenarios-between-the-two-tools).

## Keyboard Shortcuts

| Action | Shortcut |
| :--- | :--- |
| Add Car | `C` |
| Add Road | `R` |
| Add Query | `Q` |
| Edit Selected | `E` |
| Delete Selected | `Backspace` |
| Open | `Ctrl`/`Cmd` + `O` |
| Save | `Ctrl`/`Cmd` + `S` |
| Save As | `Ctrl`/`Cmd` + `Shift` + `S` |
| Export to UMLSL-Sim | `Ctrl` + `E` |
| Import from UMLSL-Sim | `Ctrl` + `I` |
| Settings | `Ctrl` + `,` (`Cmd` + `,` on macOS) |

## Tests

```bash
pip install -e '.[dev]'
pytest tests
```
