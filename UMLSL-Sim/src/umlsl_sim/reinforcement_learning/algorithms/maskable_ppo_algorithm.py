from typing import TYPE_CHECKING, Dict, Any

from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_registry import register_rl_algorithm
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm import RLAlgorithm
from umlsl_sim.reinforcement_learning.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.reinforcement_learning.algorithms.sample_ppo_params import sample_ppo_params

# Heavy deps are imported lazily so importing this module (the algorithms
# package imports every sibling for the registry side effect) does not require
# sb3-contrib to be installed.
if TYPE_CHECKING:
    import optuna
    from sb3_contrib import MaskablePPO

@register_rl_algorithm(RLAlgorithmType.MASKABLE_PPO)
class MaskablePPOAlgorithm(RLAlgorithm):
    """PPO with invalid-action masking -- the safety-shield training mechanism.

    Same optimizer as `PPOAlgorithm`; the difference is that the policy's
    action distribution is masked before sampling, so actions the environment
    reports as unavailable are never taken and never contribute to the
    gradient. Here the mask comes from
    :class:`umlsl_sim.car_control.action_shield.ActionShield`, which asks the
    same `SafetyController` the safety-aware reward consults.

    Choosing this algorithm is what enables the shield:
    `RLGameController` reads `requires_action_masks` and calls
    `MlslEnv.enable_action_shield()` before training. The reward profile stays a
    free choice -- pairing the shield with `INITIAL_REWARD` gives a reward that
    speaks only about the objective, which is the point of shielding.

    ## Hyperparameters

    Identical to PPO's, so `sample_ppo_params` is reused unchanged for Optuna
    searches. (It samples no gSDE parameters, which MaskablePPO does not
    support.)

    ## References

    - Alshiekh et al., 2018: "Safe Reinforcement Learning via Shielding"
    - sb3-contrib: https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html
    """

    requires_action_masks = True

    def create_algorithm(self, params: Dict[str, Any] | None = None) -> "MaskablePPO":
        """Create a MaskablePPO instance.

        Args:
            params (Dict[str, Any] | None): Hyperparameters. If None, uses the
                sb3-contrib defaults.

        Returns:
            MaskablePPO: An algorithm instance ready for training. It expects
                the environment to expose `action_masks()`, which `MlslEnv`
                does (all-permissive unless a shield is attached).
        """
        from sb3_contrib import MaskablePPO

        if params is None:
            return MaskablePPO("MlpPolicy", self.env)
        return MaskablePPO("MlpPolicy", self.env, **params)

    def get_sample_params(self, trial: "optuna.Trial") -> Dict[str, Any]:
        """Sample hyperparameters for Optuna optimization.

        Args:
            trial (optuna.Trial): The Optuna trial for suggesting values.

        Returns:
            Dict[str, Any]: A complete set of hyperparameters for this trial.
        """
        return sample_ppo_params(trial)
