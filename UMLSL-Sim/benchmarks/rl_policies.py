"""How the two safety mechanisms compare on a trained agent.

Produces the RL table of the paper: for each policy, how often it takes an
action the safety controller rejects, how often it crashes, how many goals it
reaches, and how long its episodes last.

The arms differ in *how* the safety controller is used, which is the paper's
point:

* ``random``           -- uniform over the whole action space; the scale.
* ``random-shielded``  -- uniform over the actions the shield leaves open. No
                          learning at all, so whatever safety it shows is the
                          shield's and not the policy's.
* ``ppo-initial``      -- PPO, reward speaks only about the objective. The
                          controller is not consulted during training.
* ``ppo-safety-aware`` -- PPO, reward penalises actions the controller rejects.
* ``maskable-ppo``     -- MaskablePPO, the controller's verdict is a mask
                          applied before the agent acts, and the reward is the
                          plain objective one.

    python rl_policies.py                       # every arm, 3 seeds
    python rl_policies.py --arms maskable-ppo   # one arm
    python rl_policies.py --train-steps 2000 --eval-episodes 2 --seeds 1  # smoke

Writes results/<scenario>/rl_<arm>.json, one file per arm, each holding the
per-seed aggregates and the per-episode records behind them.

## One controller query per step, in every arm

Counting "unsafe" actions means asking a `SafetyController` what it would have
allowed, and that question is not free of consequences: `get_max_acceleration`
withdraws the car's own crossing claim when it is fully braked and outranked at
the intersection ahead (`_drop_pending_priority`), and a car holding no claim is
never outranked afterwards. Asking twice per step would therefore let the second
answer be more permissive than the first.

So every arm asks exactly once, using whichever controller is already in its
loop rather than adding one:

* ``ppo-safety-aware`` reads the verdict its own reward computed
  (`SafetyAwareReward._pre_step`);
* the shielded arms read it off the action mask, which is that verdict
  re-encoded (the lane bits are evaluated at the largest admitted acceleration,
  so they are conservative for any acceleration the mask allows);
* ``random`` and ``ppo-initial`` have no controller in their loop, so this
  script supplies one.

The arms are therefore instrumented alike, and each runs with the same single
side effect per step.
"""

import argparse
import contextlib
import io
import json
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from umlsl_sim.car_control.action_shield import ACC_ACTIONS
from umlsl_sim.car_control.safety_controller import SafetyController
from umlsl_sim.constants import MAX_DEC
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_registry import get_rl_algo
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.reinforcement_learning.env_factory import EnvSpec
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import (
    ObservationModelType,
)
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
from umlsl_sim.scenario_io.loader import load_scenario

DEFAULT_SCENARIO = "ONE_CROSSING"
DEFAULT_SEEDS = 3
DEFAULT_TRAIN_STEPS = 100_000
DEFAULT_EVAL_EPISODES = 30

# Evaluation episodes are seeded from this, so every arm and every seed meets
# the same 30 starting configurations and the columns stay comparable.
EVAL_BASE_SEED = 4_2000


@dataclass(frozen=True)
class Arm:
    """One row of the table.

    Attributes:
        algorithm (RLAlgorithmType | None): None for the untrained baselines.
        reward (RewardType): Reward profile the environment scores by.
        shield (bool): Whether the safety shield masks the action space.
    """

    algorithm: None | RLAlgorithmType
    reward: RewardType
    shield: bool

    @property
    def trained(self) -> bool:
        return self.algorithm is not None


ARMS: dict[str, Arm] = {
    "random": Arm(None, RewardType.INITIAL_REWARD, shield=False),
    "random-shielded": Arm(None, RewardType.INITIAL_REWARD, shield=True),
    "ppo-initial": Arm(RLAlgorithmType.PPO, RewardType.INITIAL_REWARD, shield=False),
    "ppo-safety-aware": Arm(RLAlgorithmType.PPO, RewardType.SAFETY_AWARE_REWARD, shield=False),
    "maskable-ppo": Arm(RLAlgorithmType.MASKABLE_PPO, RewardType.INITIAL_REWARD, shield=True),
}


def build_spec(scenario: dict, arm: Arm) -> EnvSpec:
    """The environment recipe for one arm."""
    return EnvSpec(
        roads=scenario["roads"],
        players=scenario["players"],
        predefined_cars=scenario["predefined_cars"],
        observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
        reward_type=arm.reward,
        uses_action_masks=arm.shield,
        rl_mode=RLMode.TRAIN,
    )


def train(spec: EnvSpec, arm: Arm, seed: int, steps: int, sink: io.StringIO):
    """Train one policy, and return it with the wall-clock seconds it took.

    Hyperparameters are the Stable-Baselines3 defaults for every arm: the point
    of the table is the safety mechanism, and tuning one arm and not another
    would confound it.
    """
    with contextlib.redirect_stdout(sink):
        env, _shield = spec.build()
        algorithm = get_rl_algo(arm.algorithm)(env, {"seed": seed})
        start = time.perf_counter()
        algorithm.algorithm.learn(total_timesteps=steps, progress_bar=False)
        elapsed = time.perf_counter() - start
        env.close()
    _drain(sink)
    return algorithm.algorithm, elapsed


def _drain(sink: io.StringIO) -> None:
    sink.truncate(0)
    sink.seek(0)


def _mask_verdict(mask: np.ndarray) -> tuple[int, list[bool]]:
    """The safety controller's verdict, read back off an action mask.

    Returns:
        tuple[int, list[bool]]: The largest acceleration the mask admits, and
            the lane-change verdict indexed [right, stay, left].
    """
    allowed_acc = np.flatnonzero(mask[:ACC_ACTIONS])
    max_acc = int(allowed_acc.max()) - MAX_DEC
    return max_acc, [bool(b) for b in mask[ACC_ACTIONS:]]


def run_episode(env, arm: Arm, model, rng: random.Random,
                seed: int, instrumented: bool) -> dict:
    """Play one evaluation episode, counting what the controller would reject.

    `instrumented` asks this script to supply the controller, for the arms that
    run none of their own; the others are read instead (see the module
    docstring).
    """
    obs, _info = env.reset(seed=seed)
    unwrapped = env.unwrapped
    game_model = unwrapped.game_model

    instrument = SafetyController(
        car=game_model.agent_car,
        cars=game_model.cars,
        reservation_management=game_model.reservation_management,
    ) if instrumented else None

    steps = 0
    unsafe_acc = 0
    unsafe_lane = 0
    mask_violations = 0

    while True:
        mask = unwrapped.action_masks() if arm.shield else None

        # The verdict, from whichever controller this arm already runs.
        if arm.shield:
            max_acc, safe_lane = _mask_verdict(mask)
        elif instrument is not None:
            max_acc = instrument.get_max_acceleration()
            safe_lane = None            # needs the chosen acceleration first
        else:
            max_acc, safe_lane = None, None   # read from the env after the step

        if not arm.trained:
            action = _sample(unwrapped.action_space, mask, rng)
        elif arm.shield:
            action, _states = model.predict(obs, deterministic=True, action_masks=mask)
        else:
            action, _states = model.predict(obs, deterministic=True)

        acc = int(action[0]) - MAX_DEC
        lane = int(action[1]) - 1

        if arm.shield:
            # By construction, but a masked policy that ever slipped through
            # would be the single most important thing this table could report.
            if not mask[int(action[0])] or not mask[ACC_ACTIONS + int(action[1])]:
                mask_violations += 1
        elif instrument is not None:
            reservations = game_model.reservation_management.get_car_reservations(
                game_model.agent_car.id
            )
            safe_lane = instrument.get_safe_lane_change(reservations, acc)

        obs, _reward, done, truncated, _info = env.step(action)
        steps += 1

        if max_acc is None:
            # ppo-safety-aware: the reward already asked, on the pre-step state.
            max_acc = unwrapped.last_max_acc
            safe_lane = unwrapped.last_safe_lane_change

        unsafe_acc += acc > max_acc
        unsafe_lane += not safe_lane[lane + 1]

        if done or truncated:
            break

    end = unwrapped.episode_end
    agent = game_model.agent_car

    return {
        "steps": steps,
        "reason": end.reason if end is not None else None,
        "crashed": bool(agent.get_death_status()),
        "goals": int(agent.score),
        "unsafe_acc": int(unsafe_acc),
        "unsafe_lane": int(unsafe_lane),
        "mask_violations": mask_violations,
    }


def _sample(action_space, mask: None | np.ndarray, rng: random.Random) -> np.ndarray:
    """A uniform action, over the whole space or over what the mask allows."""
    if mask is None:
        return np.array([rng.randrange(int(n)) for n in action_space.nvec])
    acc = rng.choice(np.flatnonzero(mask[:ACC_ACTIONS]).tolist())
    lane = rng.choice(np.flatnonzero(mask[ACC_ACTIONS:]).tolist())
    return np.array([acc, lane])


def run_seed(scenario: dict, arm_name: str, arm: Arm, seed: int, train_steps: int,
             eval_episodes: int, quiet: bool) -> dict:
    """Train (if the arm learns) and evaluate one seed."""
    sink = io.StringIO()
    spec = build_spec(scenario, arm)

    model = None
    train_seconds = 0.0
    if arm.trained:
        model, train_seconds = train(spec, arm, seed, train_steps, sink)
        if not quiet:
            print(f"  {arm_name} seed={seed}: trained {train_steps} steps "
                  f"in {train_seconds / 60:.1f} min", file=sys.stderr, flush=True)

    # The arms whose loop already runs a controller are read rather than asked
    # a second time; only these two need one of ours.
    instrumented = not arm.shield and arm.reward is RewardType.INITIAL_REWARD

    with contextlib.redirect_stdout(sink):
        env, shield = spec.build()

        rng = random.Random(seed)
        records = []
        for episode in range(eval_episodes):
            records.append(run_episode(
                env, arm, model, rng, EVAL_BASE_SEED + episode, instrumented,
            ))
            _drain(sink)
        shield_stats = shield.stats() if shield is not None else None
        env.close()
    _drain(sink)

    steps = sum(r["steps"] for r in records)

    if not quiet:
        print(f"  {arm_name} seed={seed}: {steps} steps, "
              f"{sum(r['crashed'] for r in records)}/{eval_episodes} crashed, "
              f"{sum(r['goals'] for r in records)} goals",
              file=sys.stderr, flush=True)

    return {
        "seed": seed,
        "train_seconds": train_seconds,
        "steps": steps,
        "unsafe_acc_per_1000": 1000 * sum(r["unsafe_acc"] for r in records) / steps,
        "unsafe_lane_per_1000": 1000 * sum(r["unsafe_lane"] for r in records) / steps,
        "crash_rate": sum(r["crashed"] for r in records) / eval_episodes,
        "goals": sum(r["goals"] for r in records),
        "mean_episode_steps": steps / eval_episodes,
        "mask_violations": sum(r["mask_violations"] for r in records),
        "shield": shield_stats,
        "per_episode": records,
    }


def _mean_sd(values: list[float]) -> dict:
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def run_arm(scenario_key: str, arm_name: str, seeds: int, train_steps: int,
            eval_episodes: int, quiet: bool = False) -> dict:
    """Every seed of one arm, plus the aggregate across them."""
    arm = ARMS[arm_name]
    scenario = load_scenario(scenario_key)

    per_seed = [
        run_seed(scenario, arm_name, arm, seed, train_steps, eval_episodes, quiet)
        for seed in range(seeds)
    ]

    aggregate = {
        column: _mean_sd([s[column] for s in per_seed])
        for column in ("unsafe_acc_per_1000", "unsafe_lane_per_1000",
                       "crash_rate", "goals", "mean_episode_steps")
    }

    return {
        "scenario": scenario_key,
        "arm": arm_name,
        "algorithm": arm.algorithm.name if arm.algorithm else "random",
        "reward": arm.reward.name,
        "shielded": arm.shield,
        "npcs": scenario["players"],
        "seeds": seeds,
        "train_steps": train_steps if arm.trained else 0,
        "eval_episodes": eval_episodes,
        "mask_violations": sum(s["mask_violations"] for s in per_seed),
        **aggregate,
        "per_seed": per_seed,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO,
                        help=f"scenario key (default: {DEFAULT_SCENARIO})")
    parser.add_argument("--arms", nargs="+", default=list(ARMS),
                        choices=list(ARMS), help="arms to measure")
    parser.add_argument("--seeds", type=int, default=DEFAULT_SEEDS,
                        help=f"seeds per arm (default: {DEFAULT_SEEDS})")
    parser.add_argument("--train-steps", type=int, default=DEFAULT_TRAIN_STEPS,
                        help=f"training steps per seed (default: {DEFAULT_TRAIN_STEPS})")
    parser.add_argument("--eval-episodes", type=int, default=DEFAULT_EVAL_EPISODES,
                        help=f"evaluation episodes per seed (default: {DEFAULT_EVAL_EPISODES})")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "results",
                        help="directory for the result files")
    return parser


def main(argv: None | list = None) -> None:
    args = build_parser().parse_args(argv)

    # One simulation per process; torch's own thread pool only fights the other
    # arms for cores.
    import torch
    torch.set_num_threads(1)

    out_dir = args.out / args.scenario.lower()
    out_dir.mkdir(parents=True, exist_ok=True)

    for arm_name in args.arms:
        print(f"== {arm_name} ==", file=sys.stderr, flush=True)
        result = run_arm(args.scenario, arm_name, args.seeds,
                         args.train_steps, args.eval_episodes)
        (out_dir / f"rl_{arm_name}.json").write_text(json.dumps(result, indent=2))
        print(
            f"== {arm_name}: unsafe acc {result['unsafe_acc_per_1000']['mean']:.1f}/1000, "
            f"crash rate {result['crash_rate']['mean']:.2f}, "
            f"goals {result['goals']['mean']:.1f} ==",
            file=sys.stderr, flush=True,
        )


if __name__ == "__main__":
    main()
