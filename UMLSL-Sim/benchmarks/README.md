# UMLSL-Sim benchmarks

The measurements behind the simulation table in the UMLSL-TK paper: how fast
the simulator advances a frame, and how episodes end, at a range of traffic
densities. Every car is driven by the optimal controller; no RL agent takes
part, so none of this needs the `[rl]` extra.

```bash
cd UMLSL-Sim/benchmarks
python episode_outcomes.py            # collisions, gridlocks, episode lengths
python throughput.py                  # frames per second
python summarise.py                   # the LaTeX rows for the table
```

Defaults are the paper's configuration: the `TWO_CROSSINGS` scenario at 16, 24,
32, 40 and 48 cars, 30 episodes per density, each capped at 1500 frames. Pass
`--scenario`, `--cars`, `--episodes` or `--frame-cap` for anything else.

Results land in `results/<scenario>/` as JSON, one file per density, each
holding the aggregate together with the per-episode records behind it. The
committed files are the run the paper quotes.

## Why throughput is measured separately

`episode_outcomes.py` times every episode, but it runs the densities back to
back over several hours, so any drift in machine load lands on whichever
density happened to be running rather than being spread across them. On a
laptop this is not a small effect: our first attempt, with a cloud-sync daemon
awake, produced a 13x spread within one density and a curve in which 32 cars
came out slower than 40.

`throughput.py` therefore measures throughput on its own, separating the two
sources of spread that confound it. Machine contention can only ever make a
sample slower, so each fixed seed is repeated and only the fastest kept.
Variation between initial placements is a real property of the scenario, so
those per-seed bests are averaged over several placements. Densities are
interleaved round-robin. Run it on an idle machine; the per-seed spread it
prints is a reasonable check that you did.

The aggregate in the outcome files is recorded as `indicative_frames_per_second`
for exactly this reason. Quote `throughput.json`.

## Reproducibility

Each episode is seeded from its scenario, density and index, so a single
density can be re-run on its own and produce the same traffic. Outcomes are
deterministic: re-running yields identical gridlock counts, episode lengths and
goal totals, including under a randomised `PYTHONHASHSEED`. Only the timings
vary between runs.

## Comparing crossing-claim protocols

`unbounded_claim.py` runs the same benchmark with the two lease bounds of
`IntersectionState` raised past any episode length, which recovers the
behaviour the simulator had before the lease existed, where a claim once taken
was never given up. It patches the bounds in memory; no source file is touched.

```bash
python unbounded_claim.py --episodes 10
python summarise.py --compare
```

Seeds are drawn in the same order either way, so N episodes here are exactly
the first N of the bounded run and the two arms stay comparable. Ten is the
usual choice: with claims never withdrawn the traffic is far slower per frame,
around 18x at 16 cars, so an equal episode count costs disproportionately more.

Running both arms on the same scenario is the point. Figures from a different
road network measure the network as much as the protocol — the two-crossings
scenario has 75 lane segments against one-crossing's 16 — and cannot be set
beside each other.

## What counts as a gridlock

An episode ends in gridlock once every living car has stood still for
`DEADLOCK_FRAMES` consecutive frames (16, derived in `constants.py` from the
claim-lease bounds). A single frame in which nothing moves is not evidence of
one: with claims held on a lease, the withdrawal of a stalled claim can set the
traffic going again. The window is sized to outlast that withdrawal —
`PRIORITY_WITHDRAW_TICKS` ticks without progress, plus a tick to re-claim the
intersection and one to get moving — so the episode is not cut off before the
lease has had its chance.

Each episode also records `first_all_stopped`, the frame on which traffic first
stopped completely. Up to that frame the trajectory does not depend on
`DEADLOCK_FRAMES`, so it is exactly where a one-frame rule would have ended the
episode — which is what makes the effect of the window measurable rather than
assumed. In the committed run it changed no gridlock count, and fired once, at
48 cars, where traffic stopped at frame 849, recovered, and gridlocked at 880.
