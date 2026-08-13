"""How fast the simulator advances a frame, against traffic density.

Produces the throughput rows of the simulation table in the paper. It is a
separate pass from `episode_outcomes.py` because a throughput number is only
worth as much as the machine it was measured on, and two sources of spread
confound it:

* machine contention, which can only ever make a sample slower. Each fixed seed
  is therefore repeated `--reps` times and only the fastest kept.
* traffic variation between initial placements, which is a real property of the
  scenario rather than noise. Those per-seed bests are averaged over `--seeds`
  distinct placements.

Densities are interleaved round-robin so that none is systematically favoured
by when it ran -- on a laptop, an hour of thermal drift between the first
density and the last is otherwise indistinguishable from a real cost.

    python throughput.py --cars 16 24 32 40 48

Run it on an otherwise idle machine; the per-seed spread it reports is a
reasonable check that you did.
"""

import argparse
import contextlib
import io
import json
import random
import statistics
import sys
import time
from pathlib import Path

from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.simulation.traffic_environment import TrafficEnv

from episode_outcomes import BASE_SEED, DEFAULT_CARS, DEFAULT_SCENARIO

DEFAULT_FRAMES = 300      # long enough to leave the initial placement transient
DEFAULT_SEEDS = 3
DEFAULT_REPS = 5


def sample(scenario: dict, cars: int, seed: int, frames_wanted: int,
           sink: io.StringIO) -> float:
    """Seconds per frame to advance `frames_wanted` frames at this density.

    Returns NaN if the episode ended early: it did less work than the others
    and is not comparable to them.
    """
    random.seed(seed)
    with contextlib.redirect_stdout(sink):
        env = TrafficEnv(
            roads=scenario["roads"],
            players=cars,
            predefined_cars=scenario["predefined_cars"],
        )
        frames = 0
        result = None
        start = time.perf_counter()
        while result is None and frames < frames_wanted:
            result = env.play_step()
            frames += 1
        elapsed = time.perf_counter() - start
    sink.truncate(0)
    sink.seek(0)
    return elapsed / frames if frames == frames_wanted else float("nan")


def measure(scenario_key: str, cars_list: list, frames: int,
            seeds: int, reps: int, quiet: bool = False) -> dict:
    scenario = load_scenario(scenario_key)
    sink = io.StringIO()
    samples = {cars: {s: [] for s in range(seeds)} for cars in cars_list}

    for rep in range(reps):
        for seed_index in range(seeds):
            for cars in cars_list:
                value = sample(
                    scenario, cars, BASE_SEED + 1000 * cars + seed_index,
                    frames, sink,
                )
                samples[cars][seed_index].append(value)
                if not quiet:
                    print(f"rep {rep} seed {seed_index} cars={cars:3d} "
                          f"{1000 * value:8.2f} ms/frame",
                          file=sys.stderr, flush=True)

    summary = {}
    for cars in cars_list:
        per_seed_best = []
        for seed_index in range(seeds):
            usable = [v for v in samples[cars][seed_index] if v == v]  # drop NaN
            if usable:
                per_seed_best.append(min(usable))
        if not per_seed_best:
            print(f"cars={cars}: every sample ended early; raise --frames or "
                  f"lower the density", file=sys.stderr)
            continue
        ms = 1000 * statistics.fmean(per_seed_best)
        summary[cars] = {
            "ms_per_frame": ms,
            "frames_per_second": 1000 / ms,
            "per_seed_best_ms": [1000 * v for v in per_seed_best],
            "per_seed_spread_ms": 1000 * (max(per_seed_best) - min(per_seed_best)),
            "raw_seconds_per_frame": samples[cars],
        }
        if not quiet:
            print(f"cars={cars:3d}  {summary[cars]['frames_per_second']:8.1f} fps "
                  f"({ms:7.2f} ms/frame, per-seed spread "
                  f"{summary[cars]['per_seed_spread_ms']:6.2f} ms)",
                  file=sys.stderr, flush=True)

    return {"scenario": scenario_key, "frames": frames, "seeds": seeds,
            "reps": reps, "by_cars": summary}


def main(argv: None | list = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--cars", type=int, nargs="+", default=DEFAULT_CARS)
    parser.add_argument("--frames", type=int, default=DEFAULT_FRAMES,
                        help=f"frames per sample (default: {DEFAULT_FRAMES})")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS,
                        help=f"initial placements per density (default: {DEFAULT_SEEDS})")
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS,
                        help=f"repetitions of each placement (default: {DEFAULT_REPS})")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results")
    args = parser.parse_args(argv)

    result = measure(args.scenario, args.cars, args.frames, args.seeds, args.reps)
    out_dir = args.out / args.scenario.lower()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "throughput.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
