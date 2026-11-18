# UMLSL-TK talk, SBMF 2026

Slidev deck for the talk on *Edit, Check, Simulate and Train: A Toolkit for Urban
Multi-Lane Spatial Logic* (SBMF 2026, Rio de Janeiro, 02.12.2026). 23 slides, about 27.5 minutes.
Every slide has speaker notes. Each note starts with its time budget and the running total.

## Commands

```bash
npm install
npx playwright install chromium   # once, for export and the overflow check
npm run dev                       # present; press P for presenter mode with notes
npm run export                    # PDF, final state of each slide -> umlsl-tk-sbmf2026.pdf
npm run export:clicks             # PDF with one page per click step
npm run qr                        # regenerate public/qr-umlsl-tk.png (local, no web service)
npx slidev --port 3030 &          # then:
npm run check                     # overflow check of all slides (needs the dev server)
```

## Structure

| Path | Content |
| :--- | :--- |
| `slides.md` | Entry file: slides and speaker notes |
| `layouts/` | KIT 2025 layouts from `sdqbeamer.cls`: `title` (title white vertical), `default`, `picture` (picture 33/50/66 vertical) |
| `components/KitFooter.vue` | Footline: section dots, page `n/total`, date, author and short title, group name, KIT logo |
| `components/*.vue` | Diagrams (models, controllers, critical points, proof sketch, Table 1 chart) |
| `styles/index.css` | KIT colours, fonts and geometry (1 px = 1 pt of the beamer page) |
| `public/logos/` | KIT logo (converted from the template PDF) and the group logo `Logo-Green.svg` |
| `public/shots/` | Screenshots of the real tools |
| `scripts/capture/` | Drivers that produced the screenshots |

Colour rule: KIT green means brand or safe. KIT red means unsafe or collision. Greys are for everything else.

## Screenshots

All screenshots come from the real tools in this repository. None is a placeholder.

* UMLSL-Edit: `scripts/capture/edit_shots.py` runs the editor with Qt's offscreen platform at
  2x scale and saves windows and dialogs with `QWidget.grab()`:
  `QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 python scripts/capture/edit_shots.py OUT SCENE [main|menu|handoff]`
* UMLSL-Sim: `scripts/capture/sim_shots.py` runs the control GUI and saves the OpenGL frame buffer:
  `python scripts/capture/sim_shots.py OUT [one|two|handoff|agent]`. The `handoff` phase stubs out
  the editor start. The `edit_shots.py handoff` phase then opens the saved snapshot the way the
  editor does. The `agent` phase needs a saved MaskablePPO model for `two_crossings`.

Run both with the Python environment of the toolkit (`../.env/bin/python`).
