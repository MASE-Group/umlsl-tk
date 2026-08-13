import os

# Multi-car traffic sim with MultiDiscrete actions, intersections, deadlock and
# crash dynamics. Episodes cap at MAX_EPISODE_STEPS=500, so 1M steps is ~2k
# episodes at worst — enough to see a learning signal beyond initial collisions.
TRAINING_TIMESTEPS = 1_000_000

# Evaluation cadence of the final training run. EvalCallback exists to
# checkpoint the best model, and every evaluation costs TRAINING_EVAL_EPISODES
# whole episodes (up to MAX_EPISODE_STEPS each) that do *not* count towards
# TRAINING_TIMESTEPS. At eval_freq=500 that was 2500 evaluation steps per 500
# training steps: measured on two_crossings with 21 cars, 84% of the run's wall
# clock went to evaluation. 10_000 still leaves 100 checkpoint opportunities
# over a 1M-step run while cutting the overhead to ~25%.
TRAINING_EVAL_FREQ = 10_000
# Episodes differ in car placement and speed from reset to reset, so a
# single-episode score is a noisy basis for "is this the best model so far".
TRAINING_EVAL_EPISODES = 5

# Per-trial budget. Needs to comfortably exceed PPO's default n_steps=2048 so
# several policy updates happen, and must allow at least OPTUNA_TRIAL_EVALS
# EvalCallback runs so StopTrainingOnNoModelImprovement(min_evals=5,
# max_no_improvement_evals=5) can actually trigger.
HYPERPARAMS_TRAINING_TIMESTEPS = 100_000
# TPESampler and MedianPruner both have n_startup_trials=10, so anything below
# ~20 trials is effectively random search with no pruning. 50 gives the TPE
# surrogate real signal and lets the pruner cull poor trials.
OPTUNA_TRIALS = 50

# Evaluations per trial; eval_freq = HYPERPARAMS_TRAINING_TIMESTEPS // this.
# Also the number of intermediate values reported to the pruner, so it doubles
# as the resolution the pruner has to judge a trial by.
OPTUNA_TRIAL_EVALS = 10
# Pruning decisions are reported per evaluation, so the pruner's warm-up is
# counted in evaluations too — it must stay well below OPTUNA_TRIAL_EVALS or no
# trial ever lives long enough to be pruned.
OPTUNA_PRUNER_STARTUP_TRIALS = 10
OPTUNA_PRUNER_WARMUP_EVALS = 3

# Trials are independent, so they parallelise. Threads would not help: the
# simulation is pure Python and holds the GIL, so OptunaSearch runs each job in
# its own process against a study shared through file storage. Each worker is
# one small MLP plus one simulation, so the search is CPU- rather than
# memory-bound; leave a couple of cores for the OS and the parent process.
OPTUNA_PARALLEL_JOBS = max(1, min(8, (os.cpu_count() or 2) - 2))

# Hard cap on env steps per RL episode. Without this, evaluate_policy can
# hang when the agent dies but background NPCs keep running indefinitely.
MAX_EPISODE_STEPS = 500

# Reward magnitudes used by SafetyAwareReward.
REWARD_GOAL_REACHED = 50.0
REWARD_CRASH = -100.0
REWARD_UNSAFE_ACCELERATION = -1.0
REWARD_UNSAFE_LANE_CHANGE = -1.0
# Potential-based shaping coefficient: per-step reward is
# REWARD_PROGRESS_COEF * (prev_dist - cur_dist), where distance is the
# pixel-space Euclidean distance from the agent to its current goal. Positive
# when the agent moves toward the goal, negative when it moves away. Keep
# small so it does not dominate REWARD_GOAL_REACHED on a successful approach.
REWARD_PROGRESS_COEF = 0.01