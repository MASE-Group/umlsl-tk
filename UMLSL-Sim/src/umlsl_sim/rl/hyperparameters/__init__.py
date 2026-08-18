"""Hyperparameter search: Optuna over an algorithm's own parameter space.

`OptunaSearch` takes an `EnvSpec` -- a picklable recipe, not a live environment
-- so every trial builds its own world and trials can run in separate
processes. The space searched comes from the algorithm being tuned
(`RLAlgorithm.sample_params`), so tuning a new algorithm needs no change here.

Input:  an `EnvSpec` and an `RLAlgorithmType`.
Output: the best parameter dict found, saved through `rl.rl_io` and reloadable
        by a later training run.
"""
