# UMLSL-Sim

The simulation and reinforcement-learning component of the UMLSL toolkit (UMLSL-TK).

## Setup

We recommend starting a new virtual environment: 

For normal set-up:
```
python3 -m venv .env
source .env/bin/activate
pip install -e .
```

For a set-up using the reinforcement learning tools:
```
python3 -m venv .env
source .env/bin/activate
pip install -e '.[rl]'
```

Install in editable mode (`-e`): UMLSL-Sim resolves its scenario
directory relative to the package source, so a non-editable install reads
scenarios from `site-packages` instead of from this working tree.

## Quick Start

### Interactive control GUI

```bash
python -m umlsl_sim.run_control_gui
```

Pick a scenario and the number of NPC cars, start / pause / rerun the run,
configure the RL options, and save a paused run as a new scenario.

### Scripted

To run a simple traffic simulation without AI:

```python
from umlsl_sim.main import main
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.scenario_io.loader import load_scenario

main(
    **load_scenario("TWO_CROSSINGS"),   # Use predefined scenario
    render_mode=RenderMode.GUI,    # Show GUI window
    show_reservation=True          # Display segments reserved by cars
)
```

`load_scenario` returns exactly the `scenario_name` / `roads` / `players` /
`predefined_cars` keys `main()` expects, which is why `**` works.

There are also two small standalone launchers:
`python -m umlsl_sim.run_manual_drive` (drive a car with the arrow keys) and
`python -m umlsl_sim.run_scenario`, a command-line front end for everything
`main()` can do:

```bash
python -m umlsl_sim.run_scenario --scenario two_crossings --players 21

# train with reward-based safety
python -m umlsl_sim.run_scenario --no-gui --rl-mode TRAIN \
    --algorithm PPO --reward SAFETY_AWARE_REWARD

# train with the safety shield instead
python -m umlsl_sim.run_scenario --no-gui --rl-mode TRAIN \
    --algorithm MASKABLE_PPO --reward INITIAL_REWARD

python -m umlsl_sim.run_scenario --help    # all options
```

## Function Parameters

### `main()` Function Signature

```python
def main(
    scenario_name,                    # Name of the scenario (used in result paths)
    roads,                            # List of Road objects
    players,                          # Number of NPC cars
    render_mode,                      # RenderMode.GUI or RenderMode.NO_GUI
    show_reservation,                 # Show reserved segments of cars
    rl_mode=None,                     # Which RL mode to use (train, optimize, etc.)
    rl_algorithm_type=None,           # Which RL algorithm to use
    observation_model_type=None,      # How agent perceives the world
    reward_type=None,                 # Reward strategy for learning
    id_model=None,                    # ID of saved model to load
    id_history=None,                  # ID of saved episode to replay
    id_hyperparams=None,              # ID of saved hyperparameters
    predefined_cars=None              # Scenario-supplied car specs
)
```

Every parameter except the first five is RL-only and requires the optional
`[rl]` extra; passing `rl_mode` without it raises a `RuntimeError` naming the
missing dependency.

### Core Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `players` | int | Yes | Number of A\*-controlled NPC vehicles in the simulation |
| `roads` | list | Yes | Road network configuration (from `load_scenario`) |
| `predefined_cars` | list | No | Scenario-supplied car specs (from `load_scenario`) |
| `scenario_name` | str | Yes | Name of scenario (for logging/saving) |
| `render_mode` | RenderMode | Yes | `RenderMode.GUI` (show window) or `RenderMode.NO_GUI` (headless) |
| `show_reservation` | bool | Yes | Show reserved segments of cars |

Randomly placed cars each need a lane segment of their own, so `players` is
capped by the number of lane segments in the road network (plus one more
segment for the RL agent car when `rl_mode` is set). Exceeding it raises a
`ValueError` reporting both numbers.

### Reinforcement Learning Parameters

| Parameter | Type | Required | Description |
|-----------|------|---------|-------------|
| `rl_mode` | RLMode | No | Control mode (see [RL Modes](#rl-modes) below) |
| `rl_algorithm_type` | RLAlgorithmType | No | Learning algorithm |
| `observation_model_type` | ObservationModelType | No | How agent sees the world |
| `reward_type` | RewardType | No | How agent is rewarded |
| `id_model` | str | No | Timestamp to load saved model |
| `id_history` | str | No | Filename to replay saved episode |
| `id_hyperparams` | str | No | Timestamp to load optimized hyperparameters |

---

### Example: Run Different Scenarios

```python
from umlsl_sim.main import main
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.scenario_io.loader import load_scenario

# Simple circuit
main(**load_scenario("CIRCUIT"), render_mode=RenderMode.GUI, show_reservation=True)

# More complex
main(**load_scenario("TWO_CROSSINGS"), render_mode=RenderMode.GUI, show_reservation=True)

# Advanced
main(**load_scenario("BIG_SCENARIO"), render_mode=RenderMode.GUI, show_reservation=True)
```

---

## RL Modes

Control how the simulation runs. Use with `rl_mode` parameter:

### `RLMode.TRAIN`

Train an agent from scratch with default hyperparameters.

```python
main(
    **load_scenario("TWO_CROSSINGS"),
    render_mode=RenderMode.GUI,
    show_reservation=True,
    rl_mode=RLMode.TRAIN,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

**Output:** Saves trained model to `rl_results/models/`

### `RLMode.OPTIMIZE`

Find best hyperparameters using Optuna.

```python
main(
    **load_scenario("TWO_CROSSINGS"),
    render_mode=RenderMode.NO_GUI,  # Faster without rendering
    show_reservation=False,
    rl_mode=RLMode.OPTIMIZE,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

Trials run in parallel worker processes (see `OPTUNA_PARALLEL_JOBS` below) and
are pruned as soon as they fall behind the trials already finished, so a search
costs considerably less than `OPTUNA_TRIALS x HYPERPARAMS_TRAINING_TIMESTEPS`.

**Output:** Saves best hyperparameters to `rl_results/hyperparameters/`, along
with `study.log`, the shared study the workers wrote into.

### `RLMode.OPTIMIZE_AND_TRAIN`

Find best hyperparameters, then train model with them.

```python
main(
    **load_scenario("TWO_CROSSINGS"),
    render_mode=RenderMode.NO_GUI,
    show_reservation=False,
    rl_mode=RLMode.OPTIMIZE_AND_TRAIN,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

**Output:** Both hyperparameters and trained model saved

### `RLMode.LOAD_TRAINED_MODEL`

Load and run a previously trained model.

```python
main(
    **load_scenario("TWO_CROSSINGS"),
    render_mode=RenderMode.GUI,
    show_reservation=True,
    rl_mode=RLMode.LOAD_TRAINED_MODEL,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD,
    id_model="2025-10-29 18:26:52"  # Timestamp of saved model
)
```

### `RLMode.LOAD_HISTORY`

Replay a recorded episode.

```python
main(
    **load_scenario("TWO_CROSSINGS"),
    render_mode=RenderMode.GUI,
    show_reservation=True,
    rl_mode=RLMode.LOAD_HISTORY,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD,
    id_model="2025-10-29 18:26:52",      # Model that created recording
    id_history="23:41:20_1768.pkl"       # Episode to replay
)
```

`rl_algorithm_type`, `observation_model_type` and `reward_type` are required
here too, even though nothing is trained: they are what locates the recording
under `rl_results/` (see [Output Structure](#output-structure)).

---

## Rendering Modes

### `RenderMode.GUI`

Shows interactive visualization window.

```python
render_mode=RenderMode.GUI
```

### `RenderMode.NO_GUI`

Headless mode (no window).

```python
render_mode=RenderMode.NO_GUI
```

---

## RL Algorithms

The algorithm also decides **how safety is enforced**. Both mechanisms read the
same oracle — the `SafetyController` that drives the NPC cars — but they use its
verdict at different points, and either can be combined with any reward profile.

### `RLAlgorithmType.PPO`

Proximal Policy Optimization. The agent may take any action; safety is left to
the reward, so pair it with `RewardType.SAFETY_AWARE_REWARD` to penalise unsafe
accelerations and lane changes after the fact.

```python
rl_algorithm_type=RLAlgorithmType.PPO
```

### `RLAlgorithmType.MASKABLE_PPO` — safety shield

PPO with invalid-action masking ([sb3-contrib](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)).
Selecting it attaches an
[`ActionShield`](src/umlsl_sim/car_control/action_shield.py) to the environment:
before each decision the safety controller is asked which accelerations and lane
changes are safe, and everything else is removed from the agent's choice set.
Unsafe actions are therefore never taken, rather than taken and then penalised,
which frees the reward to speak only about the objective:

```python
rl_algorithm_type=RLAlgorithmType.MASKABLE_PPO
reward_type=RewardType.INITIAL_REWARD          # no safety term needed
```

Two properties worth knowing:

- **The mask is conservative, never permissive.** Gymnasium masks each action
  dimension separately, and the controller's lane-change verdict depends
  slightly on the acceleration; the shield evaluates it at the largest
  acceleration it admits, so the verdict holds for every acceleration left open.
- **It is not a hard guarantee.** In states where the controller rejects
  everything it tried, it falls back to maximal braking and the shield admits
  that. Those steps are counted (`forced_brake_steps`), and a summary is printed
  after training and evaluation. `empty_mask_steps` should always be 0.

The results directory already separates the two mechanisms, since it is keyed by
algorithm name: `rl_results/models/<scenario>/<algorithm>/<observation>/<reward>/`.

---

## Observation Models

How the agent perceives the world. Currently supported (expand with other observation models):

### `ObservationModelType.NUMERIC_OBSERVATION`

Flattened vector of normalized numeric values:
- Lane positions and directions
- Car speeds and positions
- Segment reservations

```python
observation_model_type=ObservationModelType.NUMERIC_OBSERVATION
```

---

## Reward Functions

Guidance signal for learning. Currently supported (expand with other reward types):

### `RewardType.INITIAL_REWARD`

Simple sparse reward: `+1` per goal reached, `-1` for an illegal move, `-5` on
deadlock, `-10` on crash, `0` otherwise.

```python
reward_type=RewardType.INITIAL_REWARD
```

### `RewardType.SAFETY_AWARE_REWARD`

Consults a `SafetyController` and adds potential-based distance shaping:
penalties for accelerating beyond the safe maximum and for unsafe lane changes,
a large bonus per goal, a large penalty for crashing, plus a small per-step term
proportional to the progress made toward the current goal. The magnitudes live in
[`rl_constants.py`](src/umlsl_sim/reinforcement_learning/rl_constants.py) as the
`REWARD_*` constants.

```python
reward_type=RewardType.SAFETY_AWARE_REWARD
```

---

## Common Workflows

Every snippet below assumes this preamble:

```python
from umlsl_sim.main import main
from umlsl_sim.gui.render_mode import RenderMode
from umlsl_sim.scenario_io.loader import load_scenario
from umlsl_sim.reinforcement_learning.rl_modes import RLMode
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.reinforcement_learning.gymnasium_env.observation_spaces.observation_model_types import ObservationModelType
from umlsl_sim.reinforcement_learning.gymnasium_env.reward_types import RewardType

scenario = load_scenario("TWO_CROSSINGS")
```

Everything but the first three imports needs the `[rl]` extra.

### Workflow 1: Quick Test of New Scenario

```python
# Test scenario visually
main(
    **scenario,
    render_mode=RenderMode.GUI,
    show_reservation=True
)
```

### Workflow 2: Train New Agent

```python
# Train agent from scratch
main(
    **scenario,
    render_mode=RenderMode.NO_GUI,
    show_reservation=False,
    rl_mode=RLMode.TRAIN,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

### Workflow 3: Optimize Hyperparameters

```python
main(
    **scenario,
    render_mode=RenderMode.NO_GUI,
    show_reservation=False,
    rl_mode=RLMode.OPTIMIZE,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

### Workflow 4: Optimize Then Train

```python
# Optimize hyperparameters, then train with best ones
main(
    **scenario,
    render_mode=RenderMode.NO_GUI,
    show_reservation=False,
    rl_mode=RLMode.OPTIMIZE_AND_TRAIN,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD
)
```

### Workflow 5: Test Trained Agent

```python
# Load and visualize trained model
main(
    **scenario,
    render_mode=RenderMode.GUI,
    show_reservation=True,
    rl_mode=RLMode.LOAD_TRAINED_MODEL,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD,
    id_model="2025-10-29 18:26:52"  # Replace with your model timestamp
)
```

### Workflow 6: Replay Episode

```python
# Replay a recorded episode
main(
    **scenario,
    render_mode=RenderMode.GUI,
    show_reservation=True,
    rl_mode=RLMode.LOAD_HISTORY,
    rl_algorithm_type=RLAlgorithmType.PPO,
    observation_model_type=ObservationModelType.NUMERIC_OBSERVATION,
    reward_type=RewardType.INITIAL_REWARD,
    id_model="2025-10-29 18:26:52",
    id_history="23:41:20_1768.pkl"
)
```

---

## Finding Model/History IDs

Models and episodes are saved with timestamps. Find them in:

```
rl_results/
├── models/
│   └── {scenario}/PPO/NUMERIC_OBSERVATION/INITIAL_REWARD/
│       ├── 2025-10-29 18:26:52/         ← model ID (timestamp)
│       │   ├── best_model
│       │   └── history/
│       │       ├── 23:41:20_1768.pkl    ← history ID (episode file)
│       │       └── ...
│       └── ...
└── hyperparameters/
    └── ...
```

Use the exact timestamp format: `"YYYY-MM-DD HH:MM:SS"`

---

## Advanced Usage

### Hyperparameter Configuration

Edit [`src/umlsl_sim/reinforcement_learning/rl_constants.py`](src/umlsl_sim/reinforcement_learning/rl_constants.py).
The shipped values are tuned for a real training run, not for a quick smoke
test — lower them substantially if you just want to see the pipeline work:

```python
TRAINING_TIMESTEPS = 1_000_000            # Training length
TRAINING_EVAL_FREQ = 10_000               # Steps between best-model checkpoints
TRAINING_EVAL_EPISODES = 5                # Episodes per checkpoint evaluation
HYPERPARAMS_TRAINING_TIMESTEPS = 100_000  # Optuna trial length
OPTUNA_TRIALS = 50                        # Number of optimization trials
OPTUNA_TRIAL_EVALS = 10                   # Evaluations (and pruning decisions) per trial
OPTUNA_PARALLEL_JOBS = ...                # Concurrent trials; defaults to cores - 2
MAX_EPISODE_STEPS = 500                   # Hard cap on env steps per episode
DEMO_EPISODE_STEPS = 5_000                # The same cap, for LOAD_TRAINED_MODEL only
```

**Two episode caps.** Training, evaluation and Optuna trials all cap episodes
at `MAX_EPISODE_STEPS`, which the timestep budget above is sized against.
`LOAD_TRAINED_MODEL` is a single episode that nothing is learned from, so it
uses `DEMO_EPISODE_STEPS` instead: at 500 steps a shielded agent that neither
crashes nor gridlocks ends the run in well under a minute of viewing. Raise
`DEMO_EPISODE_STEPS` to watch for longer; it does not affect training.

**Watch the evaluation budget.** Evaluations do not count towards
`TRAINING_TIMESTEPS`, but they cost the same simulation steps as training does:
each one runs `TRAINING_EVAL_EPISODES` episodes of up to `MAX_EPISODE_STEPS`.
Lowering `TRAINING_EVAL_FREQ` buys finer-grained best-model checkpoints at a
steep price — at `500` it made evaluation 84% of a training run's wall clock on
`two_crossings`.

**Parallel trials.** The hyperparameter search runs `OPTUNA_PARALLEL_JOBS`
worker processes against one shared study, each with its own simulation, so the
search scales with cores. Set it to `1` to run everything in-process (useful
when debugging a trial). The budget is the study's: workers keep taking trials
until `OPTUNA_TRIALS` of them are done, so an unlucky worker holds nobody up.

---

## Output Structure

After running with RL:

```
rl_results/
├── models/
│   └── two_crossings/PPO/NUMERIC_OBSERVATION/INITIAL_REWARD/
│       └── 2025-10-29 18:26:52/
│           ├── best_model              # Trained agent
│           └── history/                # Recorded episodes
│               ├── 23:41:20_1768.pkl
│               └── ...
└── hyperparameters/
    └── two_crossings/PPO/NUMERIC_OBSERVATION/INITIAL_REWARD/
        └── 2025-10-29 18:26:52/
            ├── best_params.parquet     # Optimized settings
            ├── trials.csv              # All trial results
            └── param_importance.html   # Visualization
```

`rl_results/` is resolved **relative to the package**, at
`src/umlsl_sim/rl_results/` — the same anchoring the scenario JSONs use. Saving
and loading therefore agree no matter which directory you launch from, so
training and your `LOAD_TRAINED_MODEL` / `LOAD_HISTORY` replays need not share a
working directory. The control GUI's "Saved model" dropdown reads the same tree
through `rl_io.RESULT_MODEL_PATH`, so it lists exactly what the controller can
load.

The first three path components after `models/` come from `scenario_name`, the
algorithm, the observation model and the reward type, which is why the LOAD_\*
modes need those enums passed even though they train nothing.

---

## Benchmarks

[`benchmarks/`](benchmarks/) holds the measurements behind the simulation table
in the UMLSL-TK paper — throughput and episode outcomes across traffic
densities — together with the recorded results, so the published numbers can be
checked without re-running anything. None of it needs the `[rl]` extra.

```bash
cd benchmarks
python episode_outcomes.py    # collisions, gridlocks, episode lengths
python throughput.py          # frames per second
python summarise.py           # the table rows
```

See [`benchmarks/README.md`](benchmarks/README.md) for why throughput is
measured in a separate pass, and for comparing crossing-claim protocols.

## Tests

UMLSL-Sim has no unit-test suite. [`manual_tests/`](manual_tests/) holds
integration checks that exercise the Gymnasium environment against the real
Stable-Baselines3 stack; they need the `[rl]` extra:

```bash
pytest manual_tests/ -v          # or: python manual_tests/test_train.py
```

The editor's suite lives in [`../UMLSL-Edit/tests/`](../UMLSL-Edit/tests/).
