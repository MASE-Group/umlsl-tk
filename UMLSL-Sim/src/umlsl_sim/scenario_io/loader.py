import json
from pathlib import Path

from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.scenario_io.car_spec import CarSpec

_DATA_DIR = Path(__file__).resolve().parent.parent / "scenarios"


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
    }
