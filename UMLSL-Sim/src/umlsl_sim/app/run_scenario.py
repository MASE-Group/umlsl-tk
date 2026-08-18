"""Command-line runner for a scenario, with or without reinforcement learning.

Run as a module:

    python -m umlsl_sim.app.run_scenario                      # plain NPC simulation
    python -m umlsl_sim.app.run_scenario --scenario circuit --players 12

Reinforcement learning needs the optional extra (``pip install -e '.[rl]'``).
Two training mechanisms handle safety, and they are chosen with ``--algorithm``:

    # reward-based safety: unsafe actions are allowed, then penalised
    python -m umlsl_sim.app.run_scenario --rl-mode TRAIN \
        --algorithm PPO --reward SAFETY_AWARE_REWARD

    # safety shield: unsafe actions are masked out before the agent acts, so
    # the reward is free to speak only about the objective
    python -m umlsl_sim.app.run_scenario --rl-mode TRAIN \
        --algorithm MASKABLE_PPO --reward INITIAL_REWARD

Watch a trained agent (the id is the timestamp directory printed at the end of
training, under ``rl_results/models/...``):

    python -m umlsl_sim.app.run_scenario --rl-mode LOAD_TRAINED_MODEL \
        --algorithm MASKABLE_PPO --reward INITIAL_REWARD --id-model "2026-08-12 14:03:21"
"""
from __future__ import annotations

import argparse
from typing import List

from umlsl_sim.scenario.loader import available_scenarios, load_scenario
from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.app.main import main

DEFAULT_SCENARIO = "two_crossings"


def _rl_choices(module_path: str, class_name: str) -> List[str]:
    """Member names of an RL option enum, or [] without the ``[rl]`` extra."""
    try:
        module = __import__(module_path, fromlist=[class_name])
    except ImportError:
        return []
    return [member.name for member in getattr(module, class_name)]


def build_parser() -> argparse.ArgumentParser:
    modes = _rl_choices("umlsl_sim.rl.modes", "RLMode")
    algorithms = _rl_choices(
        "umlsl_sim.rl.algorithms.rl_algorithm_types", "RLAlgorithmType"
    )
    observations = _rl_choices(
        "umlsl_sim.rl.observations.observation_model_types",
        "ObservationModelType",
    )
    rewards = _rl_choices(
        "umlsl_sim.rl.rewards.reward_types", "RewardType"
    )

    parser = argparse.ArgumentParser(
        prog="python -m umlsl_sim.app.run_scenario",
        description="Run a UMLSL-Sim scenario, optionally with reinforcement learning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--scenario", default=DEFAULT_SCENARIO, choices=available_scenarios(),
                        type=str.lower, metavar="NAME",
                        help=f"one of: {', '.join(available_scenarios())} "
                             f"(default: {DEFAULT_SCENARIO})")
    parser.add_argument("--players", type=int, default=None,
                        help="number of NPC cars (default: the scenario's own value)")
    parser.add_argument("--no-gui", action="store_true",
                        help="run headless; the sensible choice for training")
    parser.add_argument("--hide-reservations", action="store_true",
                        help="do not draw the cars' reserved space")

    rl = parser.add_argument_group(
        "reinforcement learning", "all of these need the optional [rl] extra"
    )
    rl.add_argument("--rl-mode", default=None, choices=modes, metavar="MODE",
                    help="one of: " + ", ".join(modes) if modes else "unavailable ([rl] extra missing)")
    rl.add_argument("--algorithm", default="PPO", choices=algorithms, metavar="ALGO",
                    help="PPO leaves safety to the reward; MASKABLE_PPO turns on the "
                         "safety shield, masking unsafe actions before the agent acts "
                         "(default: PPO)")
    rl.add_argument("--observation", default="NUMERIC_OBSERVATION", choices=observations,
                    metavar="OBS", help="observation model (default: NUMERIC_OBSERVATION)")
    rl.add_argument("--reward", default="INITIAL_REWARD", choices=rewards, metavar="REWARD",
                    help="reward profile; SAFETY_AWARE_REWARD penalises unsafe actions, "
                         "INITIAL_REWARD scores the objective alone (default: INITIAL_REWARD)")
    rl.add_argument("--id-model", default=None, metavar="ID",
                    help="saved-model timestamp, required by LOAD_TRAINED_MODEL")
    rl.add_argument("--id-history", default=None, metavar="ID",
                    help="episode-history file name, required by LOAD_HISTORY")
    rl.add_argument("--id-hyperparams", default=None, metavar="ID",
                    help="saved-hyperparameter timestamp to train with")

    return parser


def run(args: argparse.Namespace) -> None:
    scenario = load_scenario(args.scenario)
    if args.players is not None:
        scenario["players"] = args.players

    rl_kwargs = {}
    if args.rl_mode is not None:
        from umlsl_sim.rl.modes import RLMode
        from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
        from umlsl_sim.rl.observations.observation_model_types import (
            ObservationModelType,
        )
        from umlsl_sim.rl.rewards.reward_types import RewardType

        rl_kwargs = dict(
            rl_mode=RLMode[args.rl_mode],
            rl_algorithm_type=RLAlgorithmType[args.algorithm],
            observation_model_type=ObservationModelType[args.observation],
            reward_type=RewardType[args.reward],
            id_model=args.id_model,
            id_history=args.id_history,
            id_hyperparams=args.id_hyperparams,
        )

    main(
        **scenario,
        render_mode=RenderMode.NO_GUI if args.no_gui else RenderMode.GUI,
        show_reservation=not args.hide_reservations,
        **rl_kwargs,
    )


if __name__ == '__main__':
    run(build_parser().parse_args())
