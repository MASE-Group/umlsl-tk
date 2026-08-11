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
`python -m umlsl_sim.run_scenario` (one scenario, no RL) and
`python -m umlsl_sim.run_manual_drive` (drive a car with the arrow keys).

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

**Output:** Saves best hyperparameters to `rl_results/hyperparameters/`

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

Currently supported (expand with more algorithms):

### `RLAlgorithmType.PPO`

Proximal Policy Optimization.

```python
rl_algorithm_type=RLAlgorithmType.PPO
```

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
HYPERPARAMS_TRAINING_TIMESTEPS = 100_000  # Optuna trial length
OPTUNA_TRIALS = 50                        # Number of optimization trials
OPTUNA_PARALLEL_JOBS = 1                  # Parallel trials (only 1 works today)
MAX_EPISODE_STEPS = 500                   # Hard cap on env steps per episode
```

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

`rl_results/` is resolved **relative to the current working directory**, not to
the package — run your training and your `LOAD_TRAINED_MODEL` / `LOAD_HISTORY`
replays from the same directory, or the saved runs will not be found. The
control GUI's "Saved model" dropdown scans the same CWD-relative tree.

The first three path components after `models/` come from `scenario_name`, the
algorithm, the observation model and the reward type, which is why the LOAD_\*
modes need those enums passed even though they train nothing.

---

## Tests

UMLSL-Sim has no unit-test suite. [`manual_tests/`](manual_tests/) holds
integration checks that exercise the Gymnasium environment against the real
Stable-Baselines3 stack; they need the `[rl]` extra:

```bash
pytest manual_tests/ -v          # or: python manual_tests/test_train.py
```

The editor's suite lives in [`../UMLSL-Edit/tests/`](../UMLSL-Edit/tests/).
