from dataclasses import dataclass
from typing import List, Optional, Tuple

from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.road_network.road_network import LaneSegment, Road


@dataclass
class PositionRef:
    """Reference to a point on a lane by road / direction / lane / position.

    `direction` is "right" or "left" — selects from `road.right_lanes` or
    `road.left_lanes`. `position` is an absolute coordinate on the road axis:
    the x coordinate on a horizontal road, the y coordinate on a vertical one.
    The lane segment holding the point and the offset within it are derived
    from `position` by `resolve_position`.
    """
    road: str
    direction: str
    lane: int
    position: int

    @classmethod
    def from_dict(cls, data: dict) -> "PositionRef":
        return cls(
            road=data["road"],
            direction=data["direction"],
            lane=int(data["lane"]),
            position=int(data["position"]),
        )


@dataclass
class CarSpec:
    """Predefined car configuration. Any field left as None falls back to the
    existing random logic in `create_random_car` / `create_goal`.
    """
    type: CarType = CarType.NPC
    start: Optional[PositionRef] = None
    speed: Optional[int] = None
    max_speed: Optional[int] = None
    first_goal: Optional[PositionRef] = None
    second_goal: Optional[PositionRef] = None
    name: Optional[str] = None
    size: Optional[int] = None
    color: Optional[Tuple[int, int, int]] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CarSpec":
        type_str = data.get("type", "NPC").upper()
        try:
            car_type = CarType[type_str]
        except KeyError as exc:
            raise ValueError(f"Unknown car type {data.get('type')!r}; expected NPC or AGENT") from exc

        color = data.get("color")
        if color is not None:
            color = tuple(color)

        return cls(
            type=car_type,
            start=PositionRef.from_dict(data["start"]) if "start" in data else None,
            speed=int(data["speed"]) if "speed" in data and data["speed"] is not None else None,
            max_speed=int(data["max_speed"]) if "max_speed" in data and data["max_speed"] is not None else None,
            first_goal=PositionRef.from_dict(data["first_goal"]) if "first_goal" in data else None,
            second_goal=PositionRef.from_dict(data["second_goal"]) if "second_goal" in data else None,
            name=data.get("name"),
            size=int(data["size"]) if "size" in data and data["size"] is not None else None,
            color=color,
        )


def resolve_position(roads: List[Road], ref: PositionRef) -> Tuple[LaneSegment, int]:
    """Resolve a PositionRef against the active road network.

    Returns the lane segment containing `ref.position` together with the
    offset of that position from the start of the segment, measured in the
    lane's direction of travel.
    """
    road = next((r for r in roads if r.name == ref.road), None)
    if road is None:
        raise ValueError(f"Road {ref.road!r} not found in scenario")

    direction = ref.direction.lower()
    if direction == "right":
        lanes = road.right_lanes
    elif direction == "left":
        lanes = road.left_lanes
    else:
        raise ValueError(
            f"PositionRef.direction must be 'right' or 'left', got {ref.direction!r}"
        )

    if not (0 <= ref.lane < len(lanes)):
        raise ValueError(
            f"Lane index {ref.lane} out of range for road {ref.road!r} "
            f"({direction} has {len(lanes)} lanes)"
        )
    lane = lanes[ref.lane]

    for segment in lane.segments:
        if not isinstance(segment, LaneSegment):
            continue
        if min(segment.begin, segment.end) <= ref.position <= max(segment.begin, segment.end):
            return segment, abs(ref.position - segment.begin)

    axis = "x" if road.horizontal else "y"
    ranges = ", ".join(
        f"[{min(s.begin, s.end)}, {max(s.begin, s.end)}]"
        for s in lane.segments if isinstance(s, LaneSegment)
    )
    raise ValueError(
        f"Position {ref.position} ({axis} coordinate) is not on any lane segment of "
        f"{ref.road}:{direction}:{ref.lane}; lane segments cover {ranges}"
    )
