"""The episode-outcome benchmark with the crossing claim left unbounded.

Raising the two lease bounds of `IntersectionState` past any episode length
recovers the behaviour the simulator had before the lease existed, in which a
claim once taken was never given up (see the comment on them in constants.py).
Running the identical scenario, densities and seeds both ways is what licenses
the before/after comparison in the paper: figures from a different road network
measure the network as much as the protocol, and cannot be set beside these.

Everything else, including the DEADLOCK_FRAMES window, is unchanged. The bounds
are patched in memory for the life of the process; no source file is touched.

    python unbounded_claim.py --cars 16 24 32 40 48 --episodes 10

Fewer episodes than the bounded arm is the usual choice: with claims never
withdrawn the traffic is far slower per frame, so an equal episode count costs
disproportionately more. Seeds are drawn in the same order either way, so N
episodes here are exactly the first N of the bounded run.
"""

import json
import sys
from pathlib import Path

from umlsl_sim.simulation.reservations import intersection_state

# Patch before importing the benchmark, so that no environment is ever built
# while the real bounds are in force.
UNBOUNDED = 1 << 30
intersection_state.PRIORITY_REORDER_TICKS = UNBOUNDED
intersection_state.PRIORITY_WITHDRAW_TICKS = UNBOUNDED

import episode_outcomes  # noqa: E402  (deliberately imported after the patch)


def main(argv: None | list = None) -> None:
    parser = episode_outcomes.build_parser()
    parser.set_defaults(episodes=10, prefix="unbounded")
    args = parser.parse_args(argv)

    # The simulation consults these through the module namespace, so confirm
    # the patch landed there rather than trusting the assignment above.
    assert intersection_state.PRIORITY_WITHDRAW_TICKS == UNBOUNDED
    assert intersection_state.PRIORITY_REORDER_TICKS == UNBOUNDED
    print(f"claim lease disabled: reorder={intersection_state.PRIORITY_REORDER_TICKS}, "
          f"withdraw={intersection_state.PRIORITY_WITHDRAW_TICKS}",
          file=sys.stderr, flush=True)

    out_dir = args.out / args.scenario.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    for cars in args.cars:
        print(f"== {cars} cars (unbounded claim) ==", file=sys.stderr, flush=True)
        result = episode_outcomes.run_config(
            args.scenario, cars, args.episodes, args.frame_cap
        )
        result["claim"] = "unbounded"
        (out_dir / f"{args.prefix}_{cars}.json").write_text(json.dumps(result, indent=2))
        print(
            f"== {cars} cars unbounded: "
            f"{result['episodes_gridlock']}/{args.episodes} gridlock, "
            f"{result['episodes_with_collision']} with a collision, "
            f"mean length {result['mean_episode_frames']:.0f} frames ==",
            file=sys.stderr,
            flush=True,
        )


if __name__ == "__main__":
    main()
