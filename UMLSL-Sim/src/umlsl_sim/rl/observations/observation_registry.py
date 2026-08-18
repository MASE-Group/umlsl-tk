from typing import Dict, Callable
from umlsl_sim.rl.observations.observation_model_types import ObservationModelType
from umlsl_sim.rl.observations.observation_model import Observation
from umlsl_sim.rl.observations import load_plugins

_observation_registry: Dict[ObservationModelType, Observation] = {}

def register_observation_model(model_type: ObservationModelType) -> Callable[[Observation], Observation]:
    def decorator(model_class) -> Observation:
        _observation_registry[model_type] = model_class
        return model_class
    return decorator

def get_observation_model(model_type: ObservationModelType) -> Observation:
    load_plugins()
    return _observation_registry.get(model_type)