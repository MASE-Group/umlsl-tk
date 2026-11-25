# UMLSL-TK at SBMF 2026 — revised deck

Slidev source for **Edit, Check, Simulate and Train: A Toolkit for Urban Multi-Lane
Spatial Logic**, SBMF, 2 December 2026. This is an independent copy of `../slides/`;
the original is unchanged. There are **23 slides**, with a **28:25** speaking budget.
The conclusion is the final slide and includes the repository QR code. No contents
slide is included.

## Present and export

```bash
cd astra-slides
npm ci
npx playwright install chromium   # if Chromium is not already installed
npm run dev                      # http://localhost:3030
```

Open `/presenter/` for the notes and timer, or press P. Every slide has a duration,
running total, explanation, and transition in its speaker notes. Advance with the
right arrow; only four slides have staged reveals.

```bash
npm run build                    # static deck in dist/
npm run export                   # astra-umlsl-tk-sbmf2026.pdf, final states
npm run export:clicks             # a separate PDF including animation states
npm run qr                       # regenerate the repository QR locally
SLIDES=23 npm run check           # running dev server required
```

## Content distribution and pacing

The source deck's balance is retained: substantial UMLSL background and the
critical-point argument, followed by the tools' capabilities and evidence. The
original README specifies 23 slides and about 27.5 minutes. The revision retains
23 slides and the original **6:15 background / 8:35 checker** budgets. Tutorial
steps and the standalone QR closing slide are replaced by a conceptual handoff,
a simulator performance slide, and one combined conclusion.

| Part | Slides | Budget | Running time |
| :--- | :--- | ---: | ---: |
| Opening and motivating question | 1–2 | 1:30 | 1:30 |
| Reservations, chops, urban views, controller principle | 3–7 | 6:15 | 7:45 |
| UMLSL-Edit: visual modeling and readable queries | 8–9 | 2:35 | 10:20 |
| Model checking: continuous choice, critical points, proof, cost | 10–15 | 8:35 | 18:55 |
| UMLSL-Sim: scenario reuse, simulation, efficiency, RL, return | 16–22 | 8:15 | 27:10 |
| Contributions, future work, repository | 23 | 1:15 | 28:25 |

This is a **planned delivery estimate**, not a timed rehearsal by the presenter.
Approximately 3,400 words of notes include directions and source annotations;
not all should be read aloud. The allocation leaves time to point to figures and
pause at the critical-point construction. It leaves 1:35 inside a 30-minute talk
slot, before any separately scheduled discussion.

For a 25–26 minute delivery, keep every slide but shorten the explanations: save
45 seconds across the background, 20 seconds across the editor, 60 seconds across
the proof/offset discussion, and 40 seconds across simulation/RL. That targets
**25:40**. Do not rush the witness construction or redefine the metrics on the fly.
If questions are included in the slot, use this shorter delivery.

## Visual and animation choices

The existing KIT layouts, Libre Franklin headings, palette, margins, logos and
section-dot footer are retained. Native SVG figures are enlarged; explanatory
labels accompany actual screenshots. Crops are CSS viewports over the original
captures, with no fabricated UI. Screenshot colors identify cars, not verdicts.
Safety/unsafe annotations use KIT green/red and explicit text or symbols.

| Slide | Reveals | Purpose |
| ---: | ---: | :--- |
| 5 | 2 | Show withdrawal on conflict, then the reservation path |
| 10 | 1 | Isolate the continuous horizontal-chop question |
| 12 | 3 | Add offsets, midpoints, then a witnessing split |
| 20 | 1 | Compare a penalty after action with exclusion before action |

All other content is static. There are no automatic transitions. Source labels
are intentionally subordinate; essential labels and takeaways are larger.
Full-window handoff images establish context; their UI text is not a reading task.

## Evidence and scope

Primary references are `../Toolkit_for_UMLSL.pdf` and `../README.md`. Citations to
paper sections/tables appear on slides; additional interpretation is in notes.

- `TimesChart.vue` uses **paper Table 1**, checked against
  `UMLSL-Edit/benchmarks/results/timing_uniform.json`. The previous deck used a
  different, faster performance run; those numbers are not used here. Values
  remain in milliseconds internally, including F6. The axis is explicitly
  logarithmic. The fixed-view ≤2% observation is from §6.1; false gap queries can
  take longer (Table 2). No general “instant checking” claim is made.
- `SimThroughput.vue` uses **Table 3** and
  `UMLSL-Sim/benchmarks/results/two_crossings/throughput.json`. Throughput is
  headless, NPC-only simulation, computed from the mean of the best frame times
  per seed (3 seeds, 5 repeats), not GUI refresh rate. The 0 collisions and 4
  gridlocks come from 150 episodes, 30 at each of five densities.
- `PolicyResults.vue` uses **Table 4**. Goals are mean totals over **30 episodes per
  seed**, not goals per episode. Crash rates and goals are displayed; remaining
  columns and standard deviations remain in the paper. Training uses 100k steps,
  three seeds. Results concern this scenario and training budget. The paper's
  88,280 shielded steps combine random-shielded and learned-shielded evaluations.
- Runtime measurements use the paper's M1 Max / Python 3.14 / single-thread setup.
  Usability claims describe features; no authoring-time speedup was measured.
- A checked snapshot is not a proof of a future trajectory. Controller guarantees
  concern the abstract model. Scenario conversion can report representation
  adjustments, and queries are not transferred; see the repository README.

The QR encodes `https://github.com/MASE-Group/umlsl-tk`, matching the repository's
origin and the paper. It has a four-module quiet zone, no overlaid logo, and a
visible URL and label. It is 244 × 244 logical pixels on the conclusion slide.

## Preview verification

The deck was rendered in Slidev/Chromium at 1920 × 1080 and inspected as individual
slides and contact sheets. The check script captures all 23 final states and all
11 states across the four animated slides. It checks canvas/content bounds,
source-line spacing, SVG label bounds and keyboard click navigation. Captures and
its JSON result are written to ignored `preview/`.

The rendered conclusion QR was decoded successfully at 1920 × 1080, 1280 × 720,
and 960 × 540. The PDF backup is exported from Slidev. Physical projection and the
presenter's speaking pace still depend on the room and delivery.
