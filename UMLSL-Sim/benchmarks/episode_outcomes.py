"""How episodes end, and how long they take, at a range of traffic densities.

Produces the episode-outcome rows of the simulation table in the paper: how
many episodes end in a collision, in gridlock, or at the frame cap, and how
long they run. Every car is driven by the optimal controller; no RL agent takes
part.

Each episode is seeded from its scenario, density and index, so a configuration
can be re-run on its own and reproduce the same traffic. Wall-clock time is
recorded per episode, but the throughput row of the table comes from
`throughput.py` instead -- configurations here run back to back over hours, so
drift in machine load lands on whichever density happened to be running.

    python episode_outcomes.py --cars 16 24 32 40 48

Writes results/<scenario>/outcomes_<cars>.json, one file per density, each
holding the aggregate together with the per-episode records behind it.
"""

import argparse
import contextlib
import io
import json
import random
import sys
import time
from pathlib import Path

from umlsl_sim.constants import DEADLOCK_FRAMES
from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.simulation.traffic_environment import TrafficEnv

DEFAULT_SCENARIO = "TWO_CROSSINGS"
DEFAULT_CARS = [16, 24, 32, 40, 48]
DEFAULT_EPISODES = 30
DEFAULT_FRAME_CAP = 1500
BASE_SEED = 20260812


def episode_seed(cars: int, episode: int) -> int:
    """Seed for one episode. Distinct densities never share traffic."""
    return BASE_SEED + 1000 * cars + episode


def run_episode(scenario: dict, cars: int, seed: int, frame_cap: int,
                sink: io.StringIO) -> dict:
    """Play one episode to its end or to `frame_cap`, whichever comes first.

    `sink` swallows the simulator's own progress printing; pass a StringIO that
    the caller reuses across episodes.
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
        stalled = 0             # current run of consecutive all-stopped frames
        longest_stall = 0
        first_all_stopped = None
        moving_total = 0

        start = time.perf_counter()
        while result is None and frames < frame_cap:
            result = env.play_step()
            frames += 1

            moving = sum(1 for car in env.cars if car.speed > 0)
            moving_total += moving
            if moving == 0:
                stalled += 1
                longest_stall = max(longest_stall, stalled)
                if first_all_stopped is None:
                    first_all_stopped = frames
            else:
                stalled = 0
        elapsed = time.perf_counter() - start

        goals = sum(car.score for car in env.cars)
        crashes = env.total_crashes

    sink.truncate(0)
    sink.seek(0)

    return {
        "outcome": "gridlock" if result == "deadlock" else (result or "step_limit"),
        "frames": frames,
        "seconds": elapsed,
        "crashes": crashes,
        "goals": goals,
        "mean_cars_moving": moving_total / frames,
        "longest_stall": longest_stall,
        # Frame on which traffic first stopped completely. Up to this frame the
        # trajectory does not depend on DEADLOCK_FRAMES, so it is exactly where
        # a one-frame deadlock rule would have ended the episode -- which lets
        # the effect of the n-frame window be measured against that rule.
        "first_all_stopped": first_all_stopped,
    }


def run_config(scenario_key: str, cars: int, episodes: int,
               frame_cap: int, quiet: bool = False) -> dict:
    """Run every episode of one density and summarise them."""
    scenario = load_scenario(scenario_key)
    sink = io.StringIO()

    records = []
    for episode in range(episodes):
        record = run_episode(
            scenario, cars, episode_seed(cars, episode), frame_cap, sink
        )
        records.append(record)
        if not quiet:
            print(
                f"  cars={cars} ep={episode:2d} {record['outcome']:10s} "
                f"frames={record['frames']:5d} crashes={record['crashes']} "
                f"goals={record['goals']:3d} "
                f"moving={record['mean_cars_moving']:.1f} "
                f"({record['seconds']:.1f}s)",
                file=sys.stderr,
                flush=True,
            )

    total_frames = sum(r["frames"] for r in records)
    total_seconds = sum(r["seconds"] for r in records)
    gridlocks = [r for r in records if r["outcome"] == "gridlock"]
    stopped_at_all = [r for r in records if r["first_all_stopped"] is not None]

    return {
        "scenario": scenario_key,
        "cars": cars,
        "episodes": episodes,
        "frame_cap": frame_cap,
        "deadlock_frames": DEADLOCK_FRAMES,
        "episodes_with_collision": sum(1 for r in records if r["crashes"] > 0),
        "episodes_gridlock": len(gridlocks),
        "episodes_game_over": sum(1 for r in records if r["outcome"] == "game_over"),
        "episodes_step_limit": sum(1 for r in records if r["outcome"] == "step_limit"),
        "mean_episode_frames": total_frames / episodes,
        "total_goals": sum(r["goals"] for r in records),
        "mean_cars_moving": sum(r["mean_cars_moving"] for r in records) / episodes,
        "max_stall_frames": max(r["longest_stall"] for r in records),
        # Throughput here is contaminated by whatever else the machine was
        # doing; throughput.py is what the table quotes.
        "indicative_frames_per_second": total_frames / total_seconds,
        # What a one-frame deadlock rule would have reported on this same run.
        "episodes_gridlock_one_frame_rule": len(stopped_at_all),
        "per_episode": records,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO,
                        help=f"scenario key (default: {DEFAULT_SCENARIO})")
    parser.add_argument("--cars", type=int, nargs="+", default=DEFAULT_CARS,
                        help="car counts to measure")
    parser.add_argument("--episodes", type=int, default=DEFAULT_EPISODES,
                        help=f"episodes per density (default: {DEFAULT_EPISODES})")
    parser.add_argument("--frame-cap", type=int, default=DEFAULT_FRAME_CAP,
                        help=f"frames per episode (default: {DEFAULT_FRAME_CAP})")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results",
                        help="directory for the result files")
    parser.add_argument("--prefix", default="outcomes",
                        help="file name prefix (default: outcomes)")
    return parser


def main(argv: None | list = None) -> None:
    args = build_parser().parse_args(argv)
    out_dir = args.out / args.scenario.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    for cars in args.cars:
        print(f"== {cars} cars ==", file=sys.stderr, flush=True)
        result = run_config(args.scenario, cars, args.episodes, args.frame_cap)
        (out_dir / f"{args.prefix}_{cars}.json").write_text(json.dumps(result, indent=2))
        print(
            f"== {cars} cars: {result['episodes_gridlock']}/{args.episodes} gridlock, "
            f"{result['episodes_with_collision']} with a collision, "
            f"mean length {result['mean_episode_frames']:.0f} frames ==",
            file=sys.stderr,
            flush=True,
        )


if __name__ == "__main__":
    main()
