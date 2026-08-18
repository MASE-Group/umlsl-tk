from enum import Enum, auto

class RLAlgorithmType(Enum):
    PPO = auto()
    # PPO with invalid-action masking (sb3-contrib). Selecting it turns on the
    # safety shield: unsafe actions are removed from the agent's choice set
    # before it acts, instead of being penalised afterwards by the reward.
    MASKABLE_PPO = auto()