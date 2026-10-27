"""How long the model checker takes to decide a formula, against the traffic in view.

Produces the timing table of the model-checker evaluation in the paper: the
median time to decide each formula of FORMULAS for the ego car E, as E's view
holds 2, 4, 6, 8 and 10 cars while the scenario holds 40 throughout (see
scene.py), and the same over random placements for the placement table. A
sample is what the editor does when a formula is (re)checked: parse it, then
evaluate it over E's whole view, single-threaded.

    python formula_timing.py                              # the table
    python formula_timing.py --formulas F5 F6             # its slow columns
    python formula_timing.py --layouts random0 random1    # other placements
    python formula_timing.py --cars 10 --total-cars 10    # scenario size

Each formula is sampled `--repeats` times, or fewer once `--budget` seconds
are spent on it, but never fewer than `--min-repeats`. A sample still running
after `--timeout` seconds (10 minutes by default) is abandoned: the formula is
recorded as not terminating within the limit, without a verdict, and is not
sampled again. The verdict is recorded with the timings; it is deterministic,
the timings are not.

Writes results/timing_<layout>[_total<N>][_egolane].json. An existing file is
updated rather than replaced, so a slow formula can be measured in a run of its
own and land in the same file as the others.
"""

import argparse
import functools
import json
import signal
import statistics
import sys
import time
from pathlib import Path

from umlsl_edit.query.evaluator import UMLSLEvaluator

import scene

def length_is(k: int) -> str:
    # "l = k": the query language has no length equality
    return f"l >= {k} and l <= {k}"


def chop_chain(operands: list) -> str:
    """The left-nested horizontal chop ((o1 hchop o2) hchop o3) ... hchop on."""
    return functools.reduce(lambda chain, operand: f"hchop{{{chain}}}{{{operand}}}", operands[1:], operands[0])


# The formulas of the paper.
FORMULAS = {
    "F1": "<re{E}>",
    "F2": "forall c: (c != E => neg <re{E} and re{c}>)",
    "F3": "<hchop{re{E}}{l > 2 and free}>",
    "F4": "<hchop{re{E}}{l > 2 and free and neg <cs>}>",
    # Chop depth 6, counting the somewhere operator as one chop as the paper does: five left-nested
    # chops over two constants, alternating, then free. Its witness is 7 long, well within the view.
    "F5": "<" + chop_chain([length_is(1), length_is(2), length_is(1), length_is(2), length_is(1),
                            "free"]) + ">",
    # Chop depth 3, with a last operand no space in the view satisfies (E's view is about 29 long):
    # there is no witness, so the checker has to exhaust its candidates.
    "F6": "<hchop{hchop{l >= 1 and l <= 1}{l >= 2 and l <= 2}}{free and l > 100}>",
}
# F1..F4 take at most seconds; F5 and F6 up to minutes, so they have a run of their own.
TABLE_FORMULAS = ["F1", "F2", "F3", "F4"]
SLOW_FORMULAS = ["F5", "F6"]
DEFAULT_CARS_IN_VIEW = [2, 4, 6, 8, 10]
DEFAULT_REPEATS = 15
DEFAULT_MIN_REPEATS = 3
DEFAULT_BUDGET = 60.0
DEFAULT_TIMEOUT = 600.0
RESULTS = Path(__file__).parent / "results"


class _Timeout(Exception):
    pass


def _raise_timeout(signum, frame):
    raise _Timeout


def time_formula(snapshot, ego, latex: str, repeats: int, min_repeats: int, budget: float,
                 ego_lane_only: bool, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Median time to parse and decide `latex`, or a timeout record if a sample exceeds `timeout`.

    The limit is a SIGALRM interval timer, which interrupts the evaluation between two bytecodes of
    the main thread; it costs nothing while it has not fired.
    """
    evaluator = UMLSLEvaluator(snapshot)
    samples, verdicts = [], set()
    previous = signal.signal(signal.SIGALRM, _raise_timeout)
    try:
        while len(samples) < repeats:
            start = time.perf_counter()
            signal.setitimer(signal.ITIMER_REAL, timeout)
            try:
                verdicts.add(evaluator.parse_ast(latex, ego).evaluate(ego_lane_only))
            except _Timeout:
                return {"timed_out": True, "timeout_s": timeout, "median_ms": None,
                        "samples_ms": samples, "verdict": None}
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            samples.append(1000 * (time.perf_counter() - start))
            if len(samples) >= min_repeats and sum(samples) > 1000 * budget:
                break
    finally:
        signal.signal(signal.SIGALRM, previous)
    if len(verdicts) != 1:
        raise RuntimeError(f"{latex}: verdict changed between runs ({verdicts})")
    return {"timed_out": False, "median_ms": statistics.median(samples), "samples_ms": samples,
            "verdict": verdicts.pop()}


def describe(stats: dict) -> str:
    if stats["timed_out"]:
        return f"did not terminate within {stats['timeout_s']:.0f} s"
    samples = stats["samples_ms"]
    return (f"{stats['median_ms']:12.1f} ms  (n={len(samples)}, {min(samples):.1f}..{max(samples):.1f})  "
            f"-> {stats['verdict']}")


def result_path(results: Path, layout: str, total_cars: int, ego_lane_only: bool) -> Path:
    name = f"timing_{layout}"
    if total_cars != scene.DEFAULT_TOTAL_CARS:
        name += f"_total{total_cars}"
    if ego_lane_only:
        name += "_egolane"
    return results / f"{name}.json"


def measure(layout: str, cars_list: list, formulas: list, total_cars: int, repeats: int,
            min_repeats: int, budget: float, timeout: float, ego_lane_only: bool, path: Path) -> None:
    result = json.loads(path.read_text()) if path.exists() else {
        "layout": layout, "total_cars": total_cars, "ego_lane_only": ego_lane_only, "by_cars": {},
    }
    result["python"] = sys.version.split()[0]

    for cars in cars_list:
        near = scene.layout(layout, cars - 1)
        snapshot, ego = scene.build(near, total_cars)
        in_view = scene.cars_in_view(snapshot, ego)
        if len(in_view) != cars:
            print(f"warning: {layout} with {cars} cars puts {len(in_view)} in E's view: {in_view}",
                  file=sys.stderr)
        entry = result["by_cars"].setdefault(str(cars), {"formulas": {}})
        entry.update({"cars_in_view": in_view, "placements": near})
        print(f"[{layout}] {cars} cars in view ({total_cars} in the scenario)", file=sys.stderr, flush=True)

        for name in formulas:
            entry["formulas"][name] = stats = time_formula(
                snapshot, ego, FORMULAS[name], repeats, min_repeats, budget, ego_lane_only, timeout)
            print(f"    {name:8s} {describe(stats)}", file=sys.stderr, flush=True)
            # written after every formula, so an interrupted run keeps what it measured
            path.write_text(json.dumps(result, indent=1))


def main(argv: None | list = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--formulas", nargs="+", default=TABLE_FORMULAS, choices=list(FORMULAS))
    parser.add_argument("--cars", type=int, nargs="+", default=DEFAULT_CARS_IN_VIEW,
                        help="cars in E's view, E included")
    parser.add_argument("--layouts", nargs="+", default=["uniform"],
                        help="'uniform', or 'random<i>' (see scene.layout)")
    parser.add_argument("--total-cars", type=int, default=scene.DEFAULT_TOTAL_CARS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--min-repeats", type=int, default=DEFAULT_MIN_REPEATS)
    parser.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                        help=f"seconds per formula and density (default: {DEFAULT_BUDGET:.0f})")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"seconds a single sample may take (default: {DEFAULT_TIMEOUT:.0f})")
    parser.add_argument("--ego-lane-only", action="store_true",
                        help="evaluate on E's own lane only, the editor's per-query option")
    parser.add_argument("--out", type=Path, default=RESULTS)
    args = parser.parse_args(argv)

    args.out.mkdir(parents=True, exist_ok=True)
    for layout in args.layouts:
        measure(layout, args.cars, args.formulas, args.total_cars, args.repeats, args.min_repeats,
                args.budget, args.timeout, args.ego_lane_only,
                result_path(args.out, layout, args.total_cars, args.ego_lane_only))


if __name__ == "__main__":
    main()
