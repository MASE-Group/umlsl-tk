# UMLSL-Sim performance results (branch `perf/umlsl-sim`, 2026-11-19)

These numbers are not in the paper. The paper's `benchmarks/results/` predate the
claim-protocol commits `882b5a4` and `601dc00`, so they do not match the current code.

## Slide-ready summary

Two-crossings scenario, headless, NPCs driven by the optimal (A*) controller.

| Cars | Before (frames/s) | After (frames/s) | Speed-up |
|---:|---:|---:|---:|
| 16 | 264 | 2000 | 7.6x |
| 24 | 79 | 972 | 12.3x |
| 32 | 58 | 602 | 10.4x |
| 40 | 38 | 410 | 10.8x |
| 48 | 27 | 333 | 12.4x |

| RL (24 NPCs + 1 agent) | Before | After | Speed-up |
|---|---:|---:|---:|
| env step, MaskablePPO shield, safety-aware reward | 12.60 ms | 1.18 ms | 10.7x |
| env step, no shield, safety-aware reward | 15.12 ms | 1.33 ms | 11.4x |
| env step, shield, initial reward | 12.55 ms | 1.17 ms | 10.7x |
| one MaskablePPO batch (2,048 steps + 10 epochs, profiled) | 95.3 s | 13.6 s | 7.0x |

The outcomes did not change. For the same seed, the crashes, gridlocks, episode lengths,
RL observations, rewards and action masks are identical.

## Throughput per change (frames/s)

| Change | Commit | 16 | 24 | 32 | 40 | 48 |
|---|---|---:|---:|---:|---:|---:|
| Baseline | `f6cb622` | 263.8 | 79.0 | 57.8 | 38.0 | 26.9 |
| 1. Cache A* routes per (start, goal) segment | `5f4ed69` | 972.0 | 418.9 | 254.7 | 173.6 | 132.4 |
| 2. Collision test only against cars on a shared segment | `b859c94` | 1507.5 | 649.5 | 399.5 | 280.1 | 226.2 |
| 3. Route extension once per acceleration search | `f0186f7` | 1779.5 | 838.7 | 519.7 | 356.7 | 288.6 |
| 5. Crossing reservations built once per search | `a5e6f67` | 1916.0 | 936.1 | 578.8 | 392.9 | 318.1 |
| 6. Occupant lookup only for crossing segments | `ea59136` | 1999.7 | 971.7 | 601.7 | 409.9 | 333.3 |

Change 7 (`92b3e72`, one array conversion in the numeric observation) affects only the RL
path: env step 1.32 ms -> 1.18 ms. Change 4 was rejected (under 1 % gain).

## Median time per frame (ms), spread between seeds in brackets

| Cars | Baseline | After change 6 |
|---:|---:|---:|
| 16 | 4.163 (1.152) | 0.493 (0.079) |
| 24 | 13.500 (8.263) | 1.095 (0.291) |
| 32 | 15.075 (10.000) | 1.625 (0.151) |
| 40 | 26.594 (9.850) | 2.496 (0.175) |
| 48 | 33.972 (12.343) | 3.022 (0.172) |

The largest spread between the 5 repeats of one seed was 6 %.

## For reference: committed `benchmarks/results/` (old code)

| Cars | 16 | 24 | 32 | 40 | 48 |
|---|---:|---:|---:|---:|---:|
| Committed (frames/s) | 257.4 | 128.1 | 55.9 | 47.6 | 28.5 |
| Baseline, this run | 261.9 | 78.4 | 57.6 | 37.9 | 26.9 |

## Method

- Throughput: `benchmarks/throughput.py`, 300 frames, 3 seeds, 5 repeats per seed. The
  fastest repeat per seed is kept, and frames/s is the mean over the seeds.
- Each code state ran from a `git archive` export of its commit, one after another in one session.
- RL step: 400 steps with seeded random legal actions, best of 3.
- Training batch: cProfile, torch on 1 thread. In the new code, `env.step` is 80 % of the batch.
- Correctness for every change: `pytest` (726 passed), `pytest tests/integration` (57 passed),
  and `episode_outcomes.py --episodes 5` gave records identical to the baseline (25 episodes).
  For change 7, the RL ledger matched on 1,200/1,200 steps and `pytest manual_tests/` gave 38 passed.

## Machine

Apple M1 Max, 10 cores, 32 GB, macOS (Darwin 27.2.0), Python 3.14.10, numpy 2.5.5,
torch 2.15.0. CPU 80-87 % idle during the timing runs, load average 2.2-4.4.

## Raw data in this folder

- `timing/tp_base` ... `timing/tp_c6`: `throughput.json` per code state.
- `timing/rl_base.txt`, `rl_c6.txt`, `rl_c7.txt`: RL step times.
- `baseline/`: first baseline run (throughput and per-episode outcomes).
- `c*_*/`: per-episode outcomes after each change.
- `rl_ledger_*.json`: per-step RL digests used for the equality check.
