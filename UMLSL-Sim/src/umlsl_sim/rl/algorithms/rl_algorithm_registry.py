from typing import Dict, Callable
from umlsl_sim.rl.algorithms.rl_algorithm import RLAlgorithm
from umlsl_sim.rl.algorithms.rl_algorithm_types import RLAlgorithmType
from umlsl_sim.rl.algorithms import load_plugins

_rl_algo_registry: Dict[RLAlgorithmType, RLAlgorithm] = {}

def register_rl_algorithm(algo_type: RLAlgorithmType) -> Callable[[RLAlgorithm], RLAlgorithm]:
    def decorator(algo_class) -> RLAlgorithm:
        _rl_algo_registry[algo_type] = algo_class
        return algo_class
    return decorator

def get_rl_algo(algo_type: RLAlgorithmType) -> RLAlgorithm:
    load_plugins()
    return _rl_algo_registry.get(algo_type)