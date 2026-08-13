"""Turn the benchmark result files into the table rows the paper prints.

    python summarise.py                 # LaTeX rows for the simulation table
    python summarise.py --compare       # bounded vs unbounded claim

Reads whatever `episode_outcomes.py`, `throughput.py` and `unbounded_claim.py`
have left in results/<scenario>/, and says which densities are missing rather
than quietly printing a short table.
"""

import argparse
import json
from pathlib import Path

from episode_outcomes import DEFAULT_CARS, DEFAULT_SCENARIO


def load(path: Path) -> None | dict:
    return json.loads(path.read_text()) if path.exists() else None


def fmt(value: float) -> str:
    """Three significant figures, without trailing noise."""
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}"
    return f"{value:.2f}"


def latex_rows(results: dict, throughput: None | dict, cars_list: list) -> str:
    def row(label: str, cells: list) -> str:
        return f"{label:<33}& " + " & ".join(cells) + "\\\\"

    lines = [row("Cars", [str(c) for c in cars_list])]

    if throughput:
        by_cars = throughput["by_cars"]
        # JSON keys are strings; the caller's car counts are ints.
        got = {int(k): v for k, v in by_cars.items()}
        if all(c in got for c in cars_list):
            lines.append(row("Frames per second",
                             [fmt(got[c]["frames_per_second"]) for c in cars_list]))
            lines.append(row("Milliseconds / frame",
                             [f"{got[c]['ms_per_frame']:.2f}" for c in cars_list]))
        else:
            missing = [c for c in cars_list if c not in got]
            lines.append(f"% throughput rows omitted: no data for {missing}")

    lines.append(row("Episodes with a collision",
                     [str(results[c]["episodes_with_collision"]) for c in cars_list]))
    lines.append(row("Episodes ending in gridlock",
                     [str(results[c]["episodes_gridlock"]) for c in cars_list]))
    lines.append(row("Episodes reaching the step limit",
                     [str(results[c]["episodes_step_limit"]) for c in cars_list]))
    lines.append(row("Mean episode length (frames)",
                     [f"{results[c]['mean_episode_frames']:.0f}" for c in cars_list]))
    return "\n".join(lines)


def comparison(bounded: dict, unbounded: dict, cars_list: list) -> str:
    lines = [
        f"{'cars':>5} | {'gridlock':>16} | {'cars moving':>15} | "
        f"{'goals / 1000 frames':>21}",
        f"{'':>5} | {'lease':>7} {'unbdd':>8} | {'lease':>7} {'unbdd':>7} | "
        f"{'lease':>10} {'unbdd':>10}",
        "-" * 68,
    ]
    for cars in cars_list:
        b, u = bounded.get(cars), unbounded.get(cars)
        if b is None or u is None:
            lines.append(f"{cars:5d} | {'(missing)':>16}")
            continue
        bg = f"{b['episodes_gridlock']}/{b['episodes']}"
        ug = f"{u['episodes_gridlock']}/{u['episodes']}"
        bgoals = 1000 * b["total_goals"] / (b["episodes"] * b["mean_episode_frames"])
        ugoals = 1000 * u["total_goals"] / (u["episodes"] * u["mean_episode_frames"])
        lines.append(
            f"{cars:5d} | {bg:>7} {ug:>8} | "
            f"{100 * b['mean_cars_moving'] / cars:6.0f}% {100 * u['mean_cars_moving'] / cars:6.0f}% | "
            f"{bgoals:10.1f} {ugoals:10.1f}"
        )

    totals = [(sum(x[c]["episodes_gridlock"] for c in cars_list if c in x),
               sum(x[c]["episodes"] for c in cars_list if c in x))
              for x in (bounded, unbounded)]
    lines.append("")
    lines.append(f"overall gridlock: lease {totals[0][0]}/{totals[0][1]}, "
                 f"unbounded {totals[1][0]}/{totals[1][1]}")
    return "\n".join(lines)


def main(argv: None | list = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--cars", type=int, nargs="+", default=DEFAULT_CARS)
    parser.add_argument("--results", type=Path,
                        default=Path(__file__).parent / "results")
    parser.add_argument("--compare", action="store_true",
                        help="print the bounded/unbounded comparison instead")
    args = parser.parse_args(argv)

    base = args.results / args.scenario.lower()
    bounded = {c: r for c in args.cars
               if (r := load(base / f"outcomes_{c}.json")) is not None}

    missing = [c for c in args.cars if c not in bounded]
    if missing:
        print(f"% no outcome data for {missing} -- run episode_outcomes.py first")
    have = [c for c in args.cars if c in bounded]
    if not have:
        return

    if args.compare:
        unbounded = {c: r for c in args.cars
                     if (r := load(base / f"unbounded_{c}.json")) is not None}
        if not unbounded:
            print("no unbounded-claim data -- run unbounded_claim.py first")
            return
        print(comparison(bounded, unbounded, have))
    else:
        print(latex_rows(bounded, load(base / "throughput.json"), have))


if __name__ == "__main__":
    main()
