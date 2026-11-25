"""Serialize a (paused) live simulation back into a scenario JSON file.

Every car in the current world is written as a *predefined* car, so reloading
the scenario reproduces the frozen frame: same roads, same start positions,
speeds, sizes, colours and goals.

Position inversion (verified against the loader): a car's absolute axis
coordinate is ``segment.begin + car.loc`` and ``resolve_position`` reconstructs
the same segment/offset from it, including reverse-direction lanes where
``car.loc`` is negative.

The predefined-car loader accepts several cars on one lane segment as long as
their footprints do not overlap, so a collision-free frame always reloads.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.simulation.road_network.road_network import (
    CrossingSegment,
    Goal,
    LaneSegment,
    Road,
    right_direction,
)
from umlsl_sim.scenario import loader as _loader


def scenarios_dir() -> Path:
    """Directory that holds the scenario JSON files (mirrors the loader's
    ``_DATA_DIR``)."""
    return Path(_loader.__file__).resolve().parent / "scenarios"


# backwards-compatible private alias used within this module
_scenarios_dir = scenarios_dir


def _lane_direction_label(direction) -> str:
    """'right' or 'left' — the lane-group label used by PositionRef."""
    return "right" if right_direction[direction] else "left"


def _first_lane_segment(car: Car, reservation_management) -> Tuple[LaneSegment, int]:
    """Return (lane_segment, loc) describing the car's start.

    If the car currently sits on a lane segment, that segment and the car's
    ``loc`` are returned directly. If it is mid-crossing, we snap to the entry
    (loc 0) of the next lane segment in its reservations.
    """
    reservations = reservation_management.get_car_reservations(car.id)
    first = reservations[0]
    if isinstance(first.segment, LaneSegment):
        return first.segment, car.loc
    for seg_info in reservations:
        if isinstance(seg_info.segment, LaneSegment):
            return seg_info.segment, 0
    raise ValueError(f"Car {car.name!r} has no lane segment to anchor a start position")


def _position_ref(segment: LaneSegment, position: int) -> Dict:
    return {
        "road": segment.lane.road.name,
        "direction": _lane_direction_label(segment.lane.direction),
        "lane": segment.lane.num,
        "position": int(position),
    }


def _goal_ref(goal: Optional[Goal]) -> Optional[Dict]:
    if goal is None:
        return None
    seg = goal.lane_segment
    axis_pos = goal.pos.x if seg.lane.road.horizontal else goal.pos.y
    return _position_ref(seg, axis_pos)


def _next_lane_segment(car: Car, reservation_management, start: LaneSegment) -> Optional[LaneSegment]:
    """The lane segment ``car`` enters after its next crossing, from its planned route.

    The route is what the car has reserved from ``start`` on, continued with
    A* towards its goal, the way ``Car.get_next_segment`` plans it. ``None`` if
    the car has no route past the crossing.
    """
    route = [info.segment for info in reservation_management.get_car_reservations(car.id)]
    route = route[route.index(start):] if start in route else [start]
    goal = car.second_goal if car.goal is not None and car.goal.lane_segment is start else car.goal
    if goal is not None:
        route += car.astar(reservations_management=reservation_management,
                           start_seg=route[-1], goal=goal)[1:]
    crossed = False
    for segment in route[1:]:
        if isinstance(segment, CrossingSegment):
            crossed = True
        elif crossed and isinstance(segment, LaneSegment):
            return segment
    return None


def car_to_spec(car: Car, reservation_management) -> Dict:
    """Return the predefined-car spec dict for ``car``'s current state.

    Besides what the loader reads, the spec carries ``next_lane``: the lane the
    car enters after its next crossing, at that lane segment's midpoint.
    UMLSL-Sim ignores it. UMLSL-Edit reads it as the car's turn intent, because
    the goals alone do not say where the car turns next.
    """
    segment, loc = _first_lane_segment(car, reservation_management)
    position = segment.begin + loc
    spec: Dict = {
        "type": car.type.name,
        "name": car.name,
        "color": list(car.color),
        "size": int(car.size),
        "speed": int(car.speed),
        "max_speed": int(car.max_speed),
        "start": _position_ref(segment, position),
    }
    first_goal = _goal_ref(car.goal)
    if first_goal is not None:
        spec["first_goal"] = first_goal
    second_goal = _goal_ref(car.second_goal)
    if second_goal is not None:
        spec["second_goal"] = second_goal
    next_lane = _next_lane_segment(car, reservation_management, segment)
    if next_lane is not None:
        midpoint = (min(next_lane.begin, next_lane.end) + max(next_lane.begin, next_lane.end)) // 2
        spec["next_lane"] = _position_ref(next_lane, midpoint)
    return spec


def road_to_dict(road: Road) -> Dict:
    return {
        "name": road.name,
        "horizontal": road.horizontal,
        "top": road.top,
        "right": len(road.right_lanes),
        "left": len(road.left_lanes),
    }


def sanitize_stem(name: str) -> str:
    stem = re.sub(r"[^0-9a-zA-Z]+", "_", name.strip().lower()).strip("_")
    return stem or "scenario"


def unique_stem(stem: str, out_dir: Path) -> str:
    """``stem``, or ``stem_2``, ``stem_3``, … : the first one with no file in ``out_dir``."""
    candidate, n = stem, 2
    while (out_dir / f"{candidate}.json").exists():
        candidate, n = f"{stem}_{n}", n + 1
    return candidate


@dataclass
class SaveResult:
    path: Path
    n_cars: int
    n_agents: int
    snapped: List[str]  # cars snapped to a lane entry from mid-crossing


def save_current_scenario(
    game_model: TrafficEnv,
    display_name: str,
    out_dir: Optional[Path] = None,
    overwrite: bool = False,
    unique: bool = False,
) -> SaveResult:
    """Write ``game_model``'s current state to ``<stem>.json`` and return a
    :class:`SaveResult`. Raises ``FileExistsError`` if the target exists and
    ``overwrite`` is False, ``ValueError`` on an empty world.

    With ``unique``, a taken name gets the first free suffix (``_2``, ``_3``, …)
    instead, so the save never fails or replaces a file."""
    rm = game_model.reservation_management
    cars = list(game_model.cars)
    if not cars:
        raise ValueError("There are no cars to save.")

    out_dir = out_dir or _scenarios_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = sanitize_stem(display_name)
    if unique:
        stem = unique_stem(stem, out_dir)
    path = out_dir / f"{stem}.json"
    if path.exists() and not overwrite:
        raise FileExistsError(str(path))

    car_specs: List[Dict] = []
    snapped: List[str] = []
    n_agents = 0

    for car in cars:
        reservations = rm.get_car_reservations(car.id)
        if not isinstance(reservations[0].segment, LaneSegment):
            snapped.append(car.name)
        spec = car_to_spec(car, rm)
        car_specs.append(spec)
        if spec["type"] == "AGENT":
            n_agents += 1

    # NPC count = cars written as NPCs, so the loader adds no random top-ups.
    n_npcs = sum(1 for s in car_specs if s["type"] == "NPC")

    data = {
        "name": stem.upper(),
        "scenario_name": stem,
        "players": n_npcs,
        # the world the scenario runs in, so that it reloads (and opens in the editor) at the same size
        "width": game_model.world_size[0],
        "height": game_model.world_size[1],
        "roads": [road_to_dict(r) for r in game_model.roads],
        "cars": car_specs,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    return SaveResult(
        path=path,
        n_cars=len(car_specs),
        n_agents=n_agents,
        snapped=snapped,
    )
