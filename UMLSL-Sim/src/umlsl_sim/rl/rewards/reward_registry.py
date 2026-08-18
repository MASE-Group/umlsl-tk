from typing import Dict, Callable
from umlsl_sim.rl.gym_env.umlsl_env import MlslEnv
from umlsl_sim.rl.rewards.reward_types import RewardType
from umlsl_sim.rl.rewards import load_plugins

_reward_registry: Dict[RewardType, MlslEnv] = {}

def register_reward_model(model_type: RewardType) -> Callable[[MlslEnv], MlslEnv]:
    def decorator(model_class) -> MlslEnv:
        _reward_registry[model_type] = model_class
        return model_class
    return decorator

def get_reward_model(model_type: RewardType) -> MlslEnv:
    load_plugins()
    return _reward_registry.get(model_type)