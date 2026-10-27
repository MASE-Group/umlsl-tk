"""Turn the benchmark result files into the table rows the paper prints.

    python summarise.py                 # LaTeX rows for the timing table
    python summarise.py --placement     # LaTeX rows for the placement table
    python summarise.py --spread        # placements and scenario size, for the text

Reads whatever formula_timing.py has left in results/, and says which
configurations are missing rather than quietly printing a short table.
"""

import argparse
import json
import statistics
from pathlib import Path

from formula_timing import DEFAULT_CARS_IN_VIEW, RESULTS, SLOW_FORMULAS, TABLE_FORMULAS

# The placement table's formulas: those a random placement can make false.
PLACEMENT_FORMULAS = ["F3", "F4"]


def load(path: Path) -> None | dict:
    return json.loads(path.read_text()) if path.exists() else None


def random_results(results: Path) -> list:
    return [load(path) for path in sorted(results.glob("timing_random*.json"))
            if "_total" not in path.name and "_egolane" not in path.name]


TIMED_OUT = "t/o"      # the tables' captions say what it means: no verdict within the timeout


def ms(stats: dict) -> str:
    return TIMED_OUT if stats["timed_out"] else f"{stats['median_ms']:.1f}"


def seconds(stats: dict) -> str:
    return TIMED_OUT if stats["timed_out"] else f"{stats['median_ms'] / 1000:.1f}"


def timing_rows(results: Path) -> str:
    timing = load(results / "timing_uniform.json")
    if timing is None:
        return "% no timing data -- run formula_timing.py first"
    lines = []
    for cars in DEFAULT_CARS_IN_VIEW:
        formulas = timing["by_cars"].get(str(cars), {}).get("formulas", {})
        cells = [ms(formulas[f]) if f in formulas else "--" for f in TABLE_FORMULAS]
        cells += [seconds(formulas[f]) if f in formulas else "--" for f in SLOW_FORMULAS]
        lines.append(f"{cars:<17} & " + " & ".join(f"{c:>7}" for c in cells) + " \\\\")
        missing = [f for f in TABLE_FORMULAS + SLOW_FORMULAS if f not in formulas]
        if missing:
            lines.append(f"% {cars} cars: no data for {missing}")
        wrong = [f for f in TABLE_FORMULAS + ["F5"] if f in formulas and formulas[f]["verdict"] is False]
        if wrong:
            lines.append(f"% {cars} cars: {wrong} did not hold")
    return "\n".join(lines)


def placement_rows(results: Path) -> str:
    """Per density: the uniform times, then the random placements on which the formulas hold and
    those on which they are false, each as the number of placements and the median over them of
    each placement's median, in whole milliseconds."""
    timing, randoms = load(results / "timing_uniform.json"), random_results(results)
    if timing is None or not randoms:
        return "% need timing_uniform.json and timing_random*.json"
    lines = []
    for cars in DEFAULT_CARS_IN_VIEW:
        uniform = timing["by_cars"].get(str(cars), {}).get("formulas", {})
        placements = [r["by_cars"][str(cars)]["formulas"] for r in randoms if str(cars) in r["by_cars"]]
        placements = [p for p in placements if all(f in p for f in PLACEMENT_FORMULAS)]
        cells = [f"{uniform[f]['median_ms']:.0f}" if f in uniform else "--" for f in PLACEMENT_FORMULAS]
        for holds in (True, False):
            group = [p for p in placements if p[PLACEMENT_FORMULAS[0]]["verdict"] is holds]
            cells.append(str(len(group)))
            cells += [f"{statistics.median(p[f]['median_ms'] for p in group):.0f}" if group else "--"
                      for f in PLACEMENT_FORMULAS]
        lines.append(f"{cars:<17} & " + " & ".join(f"{c:>5}" for c in cells) + " \\\\")
        if len(placements) != len(randoms):
            lines.append(f"% {cars} cars: data for {len(placements)} of {len(randoms)} placements")
        if any(len({p[f]["verdict"] for f in PLACEMENT_FORMULAS}) != 1 for p in placements):
            lines.append(f"% {cars} cars: {PLACEMENT_FORMULAS} disagree on some placement")
    return "\n".join(lines)


def spread(results: Path) -> str:
    lines = []
    by_formula: dict = {}
    for result in random_results(results):
        for cars, entry in result["by_cars"].items():
            for name, stats in entry["formulas"].items():
                by_formula.setdefault((name, int(cars)), []).append(
                    (stats, len(entry["cars_in_view"]) == int(cars)))
    if by_formula:
        lines.append("random placements: per-placement medians, min / median / max in ms")
        for (name, cars), values in sorted(by_formula.items()):
            timed_out = sum(1 for stats, _ in values if stats["timed_out"])
            times = sorted(stats["median_ms"] for stats, _ in values if not stats["timed_out"])
            summary = (f"{times[0]:9.1f} {times[len(times) // 2]:9.1f} {times[-1]:9.1f}"
                       if times else "")
            lines.append(f"  {name:8s} {cars:2d} cars: {len(values):2d} placements  {summary}"
                         f"   timed out: {timed_out}   always held: "
                         f"{all(stats['verdict'] for stats, _ in values)}   "
                         f"in view as intended: {all(ok for _, ok in values)}")

    for path in sorted(results.glob("timing_*_total*.json")):
        other = load(path)
        base = load(results / f"timing_{other['layout']}.json")
        lines.append(f"scenario of {other['total_cars']} cars against {base['layout']}'s 40:")
        for cars, entry in other["by_cars"].items():
            for name, stats in entry["formulas"].items():
                ref = base["by_cars"].get(cars, {}).get("formulas", {}).get(name)
                ref_text = f"{ms(ref):>9} ms" if ref else "(no 40-car data)"
                lines.append(f"  {name:8s} {cars:>2} cars in view: {ms(stats):>9} ms vs {ref_text}")

    for path in sorted(results.glob("timing_*_egolane.json")):
        lines.append(f"{path.name}:")
        for cars, entry in load(path)["by_cars"].items():
            for name, stats in entry["formulas"].items():
                lines.append(f"  {name:8s} {cars:>2} cars in view: {ms(stats):>9} ms")
    return "\n".join(lines) or "no placement, scenario-size or ego-lane data"


def main(argv: None | list = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--placement", action="store_true", help="print the placement table")
    parser.add_argument("--spread", action="store_true",
                        help="print the placement and scenario-size summaries")
    args = parser.parse_args(argv)

    if args.placement:
        print(placement_rows(args.results))
    elif args.spread:
        print(spread(args.results))
    else:
        print(timing_rows(args.results))


if __name__ == "__main__":
    main()
