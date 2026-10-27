"""Where the model checker finds a formula's witness, and how much searching it took.

A diagnostic for the timing table rather than a measurement: it decides one
formula once, counting the splits the horizontal chops try and the atoms they
evaluate, and reports the first observed space on which `free` held. It is what
explains F5's times: how many splits its chops try before they reach its
witness, and why that number depends on where the cars are rather than only on
how many there are.

    python trace_witness.py F5 --cars 10
"""

import argparse
import time
from collections import Counter

from umlsl_edit.query.ast import chop_node, free_node, horizon_cmp_node, reserve_node
from umlsl_edit.query.evaluator import UMLSLEvaluator

import scene
from formula_timing import FORMULAS

calls: Counter = Counter()
first_free: list = []


def instrument() -> None:
    def counting(cls, name, record=None):
        original = cls.evaluate

        def evaluate(self, traffic_snapshot, view, variable_car_map):
            calls[name] += 1
            holds = original(self, traffic_snapshot, view, variable_car_map)
            if record is not None and holds and not record:
                record.append((len(view.virtual_lanes), view.horizon.start, view.horizon.end))
            return holds
        cls.evaluate = evaluate

    counting(free_node.FreeNode, "free", first_free)
    counting(horizon_cmp_node.HorizonComparisonNode, "length comparisons")
    counting(reserve_node.ReserveNode, "re")

    original_split = chop_node.HorizontalChopNode.evaluate_at_split

    def evaluate_at_split(self, view, traffic_snapshot, variable_car_map, split_value):
        calls["horizontal splits"] += 1
        return original_split(self, view, traffic_snapshot, variable_car_map, split_value)
    chop_node.HorizontalChopNode.evaluate_at_split = evaluate_at_split


def main(argv: None | list = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("formula", choices=list(FORMULAS))
    parser.add_argument("--cars", type=int, default=10, help="cars in E's view, E included")
    parser.add_argument("--layout", default="uniform")
    args = parser.parse_args(argv)

    snapshot, ego = scene.build(scene.layout(args.layout, args.cars - 1))
    view = ego.environment.horizon
    print(f"cars in E's view: {scene.cars_in_view(snapshot, ego)}; view [{view.start}, {view.end}]")

    instrument()
    start = time.perf_counter()
    verdict = UMLSLEvaluator(snapshot).parse_ast(FORMULAS[args.formula], ego).evaluate(False)
    elapsed = 1000 * (time.perf_counter() - start)

    print(f"{args.formula} is {verdict}, decided in {elapsed:.1f} ms")
    for name, count in sorted(calls.items()):
        print(f"    {name:20s} {count:10d}")
    if first_free:
        lanes, start, end = first_free[0]
        print(f"free first held on {lanes} lane(s) over [{start:.4f}, {end:.4f}]")


if __name__ == "__main__":
    main()
