import json
from pathlib import Path
from typing import Tuple

from umlsl_sim.config.logic_constants import WORLD_HEIGHT, WORLD_WIDTH
from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.factories.car_spec import CarSpec

#: The bundled scenario files, next to this module.
_DATA_DIR = Path(__file__).resolve().parent / "scenarios"


def available_scenarios() -> list[str]:
    """Keys of the bundled scenarios, sorted, as accepted by `load_scenario`."""
    return sorted(p.stem for p in _DATA_DIR.glob("*.json"))


def world_size_of(data: dict) -> Tuple[int, int]:
    """The world a scenario file asks for: its ``width`` and ``height`` in pixels.

    Both are optional. A scenario without them gets the world every scenario had
    before they existed (`DEFAULT_WORLD_SIZE`), which is also the one every
    trained RL model was trained on. UMLSL-Edit writes them, because its world
    grows with the scenario.

    Raises:
        ValueError: If a size is not a positive whole number of pixels.
    """
    size = (data.get("width", WORLD_WIDTH), data.get("height", WORLD_HEIGHT))
    for name, value in zip(("width", "height"), size):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"Scenario {name} must be a positive whole number of pixels, got {value!r}.")
    return size


def load_scenario(scenario_key: str) -> dict:
    filepath = _DATA_DIR / f"{scenario_key.lower()}.json"
    with open(filepath) as f:
        data = json.load(f)
    roads = [Road(r["name"], r["horizontal"], r["top"], r["right"], r["left"]) for r in data["roads"]]
    predefined_cars = [CarSpec.from_dict(c) for c in data.get("cars", [])]
    return {
        "roads": roads,
        "players": data["players"],
        "scenario_name": data["scenario_name"],
        "predefined_cars": predefined_cars,
        "world_size": world_size_of(data),
    }
