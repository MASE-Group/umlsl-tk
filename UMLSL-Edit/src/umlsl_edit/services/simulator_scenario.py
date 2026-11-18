"""
Translate an editor snapshot into a UMLSL-Sim scenario, and report why it would
not run.

The two tools share a y-up world but differ in origin, unit and lane order:

                       Editor                          Simulator
    unit             1 lane                          40 px (``UNIT``)
    origin           canvas centre                   bottom-left corner
    canvas           unbounded                       40 x 24 lanes, a torus:
                                                     every road spans the canvas
                                                     and wraps at its edges
    road position    centre line                     ``top``: lowest edge
    horizontal road  forward = +x, below centre      ``right`` = +x, ``left`` = -x
    vertical road    forward = +y, east of centre    ``right`` = -y (west),
                                                     ``left`` = +y (east)
    lane order       0 / -1 next to the centre line  ``right`` lanes counted from
                     counting outwards               the road's low edge, ``left``
                                                     lanes from the centre line
    car anchor       rear of the car                 rear of the car
    turning          explicit turn intent            implicit, via a goal

The simulator only places cars and goals on *lane segments*, the stretches of a
lane between two crossings, and needs a road along each canvas edge so that the
wrap-around is a real crossing. ``build_simulator_scenario`` adds any missing
border road, maps every road, car and turn intent, and collects every reason the
result would fail to load or run as ``SimulationIssue`` objects.

The way back (``ExternalPersistenceService.deserialize``) uses the inverses
defined at the end of this module: ``unmap_road`` and ``unmap_lane`` for roads
and lanes, ``unmap_turn`` to turn a goal back into a turn intent, and
``removable_border_roads`` to drop the border roads the export adds again.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Final

from PIL import ImageColor

UNIT: Final[int] = 40
"""Simulator pixels per editor lane."""
WIDTH_LANES: Final[int] = 40
"""Simulator canvas width, in lanes."""
HEIGHT_LANES: Final[int] = 24
"""Simulator canvas height, in lanes."""

Segment = tuple[int, int]
"""A lane segment as its (low, high) interval on the road's axis, in pixels."""


class Severity(Enum):
    ERROR = "error"
    """UMLSL-Sim cannot load or run the scenario."""
    WARNING = "warning"
    """The scenario runs, but differs from what the editor shows."""


@dataclass(frozen=True)
class SimulationIssue:
    severity: Severity
    message: str


@dataclass
class SimulatorScenario:
    """The interchange payload plus everything found wrong while building it."""

    payload: dict[str, Any]
    issues: list[SimulationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[SimulationIssue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[SimulationIssue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def can_run(self) -> bool:
        return not self.errors


@dataclass
class SimRoad:
    """A road in simulator terms: ``top`` is its lowest edge, in pixels."""

    name: str
    horizontal: bool
    top: int
    right: int
    left: int
    border: bool = False

    @property
    def bottom(self) -> int:
        """Its highest edge, in pixels (the simulator's name for it)."""
        return self.top + (self.right + self.left) * UNIT

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "horizontal": self.horizontal,
            "top": self.top,
            "right": self.right,
            "left": self.left,
        }


def _extent_across(horizontal: bool) -> int:
    """Canvas size across roads of this orientation, in pixels."""
    return (HEIGHT_LANES if horizontal else WIDTH_LANES) * UNIT


def _extent_along(horizontal: bool) -> int:
    """Canvas size along roads of this orientation, in pixels."""
    return (WIDTH_LANES if horizontal else HEIGHT_LANES) * UNIT


def along_offset(horizontal: bool) -> float:
    """Editor -> simulator shift along a road of this orientation, in lanes."""
    return WIDTH_LANES / 2 if horizontal else HEIGHT_LANES / 2


def across_offset(horizontal: bool) -> float:
    """Editor -> simulator shift across a road of this orientation, in lanes."""
    return HEIGHT_LANES / 2 if horizontal else WIDTH_LANES / 2


def map_road(road: dict[str, Any]) -> SimRoad:
    """An editor road (``to_dict`` form) in simulator terms."""
    horizontal = road.get("orientation") == "HORIZONTAL"
    forward = int(road.get("number_of_forward_lanes", 0))
    backward = int(road.get("number_of_backward_lanes", 0))
    # Horizontal: forward lanes run +x below the centre line, the simulator's
    # "right" lanes. Vertical: forward lanes run +y east of the centre line, the
    # simulator's "left" lanes. Either way "right" lanes sit on the low side.
    right, left = (forward, backward) if horizontal else (backward, forward)
    low_edge = float(road.get("position", 0.0)) + across_offset(horizontal) - right
    return SimRoad(
        name=str(road.get("name", "")),
        horizontal=horizontal,
        top=round(low_edge * UNIT),
        right=right,
        left=left,
    )


def map_lane(road: SimRoad, lane_index: int) -> tuple[str, int]:
    """Editor lane index on ``road`` -> simulator (direction, lane)."""
    if road.horizontal:
        if lane_index >= 0:
            return "right", road.right - 1 - lane_index
        return "left", -lane_index - 1
    if lane_index >= 0:
        return "left", lane_index
    return "right", road.right + lane_index


def unmap_lane(horizontal: bool, right: int, direction: str, lane: int) -> int:
    """Simulator (direction, lane) -> editor lane index. Inverse of ``map_lane``."""
    if horizontal:
        return right - 1 - lane if direction == "right" else -lane - 1
    return lane if direction == "left" else lane - right


def lane_segments(crossing_roads: Iterable[SimRoad]) -> list[Segment]:
    """
    Lane segments along a road, given the roads that cross it.

    Mirrors ``umlsl_sim.factories.create_segments``: a segment runs from one
    crossing to the next, and nothing lies beyond the last crossing because the
    lane wraps around there.
    """
    segments = []
    last = 0
    for road in sorted(crossing_roads, key=lambda r: r.top):
        if road.top > last:
            segments.append((last, road.top))
        last = road.bottom
    return segments


def _segment_index(segments: list[Segment], position: float) -> int | None:
    for i, (low, high) in enumerate(segments):
        if low <= position <= high:
            return i
    return None


def _midpoint(segment: Segment) -> int:
    return (segment[0] + segment[1]) // 2


def _unique_name(base: str, taken: set[str]) -> str:
    name, n = base, 2
    while name in taken:
        name, n = f"{base}_{n}", n + 1
    taken.add(name)
    return name


def border_roads(roads: list[SimRoad]) -> list[SimRoad]:
    """
    One-lane roads for each canvas edge that no road occupies yet.

    Together they form the counter-clockwise ring the scenarios shipped with
    UMLSL-Sim use. An edge counts as occupied when a road of the matching
    orientation touches it, so round trips from the simulator stay stable.
    """
    taken = {r.name for r in roads}
    width, height = WIDTH_LANES * UNIT, HEIGHT_LANES * UNIT
    edges: list[tuple[str, bool, int, int, int, Callable[[SimRoad], bool]]] = [
        ("bottom", True, 0, 1, 0, lambda r: r.horizontal and r.top == 0),
        ("right", False, width - UNIT, 0, 1, lambda r: not r.horizontal and r.bottom == width),
        ("top", True, height - UNIT, 0, 1, lambda r: r.horizontal and r.bottom == height),
        ("left", False, 0, 1, 0, lambda r: not r.horizontal and r.top == 0),
    ]
    return [
        SimRoad(_unique_name(name, taken), horizontal, top, right, left, border=True)
        for name, horizontal, top, right, left, occupies in edges
        if not any(occupies(r) for r in roads)
    ]


def _describe(road: SimRoad) -> str:
    return f"the {road.name} border road UMLSL-Sim adds" if road.border else f"road '{road.name}'"


def _canvas_hint(horizontal: bool) -> str:
    half = (HEIGHT_LANES if horizontal else WIDTH_LANES) // 2
    axis = "y" if horizontal else "x"
    kind = "Horizontal" if horizontal else "Vertical"
    return f"{kind} roads must lie within {axis} = {-half + 1} … {half - 1}."


def _check_roads(user_roads: list[SimRoad], all_roads: list[SimRoad]) -> list[SimulationIssue]:
    issues = []
    for road in user_roads:
        if road.top < 0 or road.bottom > _extent_across(road.horizontal):
            issues.append(SimulationIssue(
                Severity.ERROR,
                f"Road '{road.name}' lies outside the UMLSL-Sim canvas. {_canvas_hint(road.horizontal)}",
            ))
    for horizontal in (True, False):
        parallel = sorted((r for r in all_roads if r.horizontal == horizontal), key=lambda r: r.top)
        for low, high in zip(parallel, parallel[1:]):
            if high.top >= low.bottom:
                continue
            if low.border or high.border:
                border, road = (low, high) if low.border else (high, low)
                if road.top < 0 or road.bottom > _extent_across(horizontal):
                    continue  # already reported as outside the canvas
                message = f"Road '{road.name}' overlaps {_describe(border)}. {_canvas_hint(horizontal)}"
            else:
                message = (f"Roads '{low.name}' and '{high.name}' overlap. "
                           f"UMLSL-Sim cannot simulate overlapping parallel roads.")
            issues.append(SimulationIssue(Severity.ERROR, message))
    return issues


def _color(value: Any) -> list[int]:
    try:
        return list(ImageColor.getrgb(str(value))[:3])
    except ValueError:
        return [0, 0, 0]  # the editor draws unknown colour names in black, too


@dataclass
class _PlacedCar:
    name: str
    road: SimRoad
    direction: str
    lane: int
    rear: int
    size: int
    positive: bool
    segment: int

    def footprint(self) -> Segment:
        return (self.rear, self.rear + self.size) if self.positive else (self.rear - self.size, self.rear)


class _Network:
    """The simulator's road network: all roads and their lane segments."""

    def __init__(self, roads: list[SimRoad]):
        self.roads = roads
        self._segments = {
            horizontal: lane_segments(r for r in roads if r.horizontal != horizontal)
            for horizontal in (True, False)
        }

    def segments_along(self, road: SimRoad) -> list[Segment]:
        return self._segments[road.horizontal]

    def crossing_at(self, road: SimRoad, position: float) -> SimRoad | None:
        return next(
            (r for r in self.roads if r.horizontal != road.horizontal and r.top <= position <= r.bottom),
            None,
        )

    @property
    def capacity(self) -> int:
        """Number of lane segments: the most cars UMLSL-Sim will place."""
        return sum((r.right + r.left) * len(self.segments_along(r)) for r in self.roads)


def build_simulator_scenario(
        snapshot_data: dict[str, Any],
        scenario_key: str,
        max_speed: float | None = None,
) -> SimulatorScenario:
    """
    Build the UMLSL-Sim interchange payload for a snapshot.

    Args:
        snapshot_data: The snapshot as returned by ``TrafficSnapshotModel.to_dict``.
        scenario_key: The scenario's file stem; ``load_scenario`` looks it up in lower case.
        max_speed: The editor's global maximum speed, exported as every car's
            ``max_speed``. ``None`` falls back to each car's current speed.

    Returns:
        The payload, plus every issue found. The payload is complete even when
        there are errors, but UMLSL-Sim will then refuse to load or run it.
    """
    issues: list[SimulationIssue] = []
    editor_roads = snapshot_data.get("roads", [])
    editor_cars = snapshot_data.get("cars", [])

    if not editor_roads:
        issues.append(SimulationIssue(
            Severity.ERROR, "The scenario has no roads. Add at least one road with a car on it."))
    if not editor_cars:
        issues.append(SimulationIssue(
            Severity.ERROR, "The scenario has no cars. Add at least one car to simulate."))

    road_by_uid = {r.get("uid"): map_road(r) for r in editor_roads}
    user_roads = list(road_by_uid.values())
    network = _Network(user_roads + border_roads(user_roads))
    issues += _check_roads(user_roads, network.roads)

    placed: list[_PlacedCar] = []
    external_cars = []
    for car in editor_cars:
        name = str(car.get("name", ""))
        road = road_by_uid.get(car.get("road_uid"))
        if road is None:
            issues.append(SimulationIssue(Severity.ERROR, f"Car '{name}' is not on a known road."))
            continue

        lane_index = int(car.get("lane_index", 0))
        direction, lane = map_lane(road, lane_index)
        positive = lane_index >= 0
        rear = round((float(car.get("position_on_lane", 0.0)) + along_offset(road.horizontal)) * UNIT)
        size = round(float(car.get("length", 1.0)) * UNIT)
        speed = float(car.get("speed", 0.0))
        segments = network.segments_along(road)
        segment = _segment_index(segments, rear)

        if not 0 <= rear <= _extent_along(road.horizontal):
            axis, half = ("x", WIDTH_LANES // 2) if road.horizontal else ("y", HEIGHT_LANES // 2)
            issues.append(SimulationIssue(
                Severity.ERROR,
                f"Car '{name}' is outside the UMLSL-Sim canvas. Place it within {axis} = {-half} … {half}.",
            ))
            segment = None
        elif segment is None:
            crossing = network.crossing_at(road, rear)
            where = f" where '{road.name}' meets {_describe(crossing)}" if crossing else ""
            issues.append(SimulationIssue(
                Severity.ERROR,
                f"Car '{name}' starts inside the crossing{where}. "
                f"UMLSL-Sim places cars on lanes only: move the rear of the car out of the crossing.",
            ))
        if speed < 0:
            issues.append(SimulationIssue(
                Severity.ERROR,
                f"Car '{name}' drives backwards (speed {speed:g}). UMLSL-Sim cars only drive forwards.",
            ))
        if float(car.get("transition", 0.0)) != 0.0:
            issues.append(SimulationIssue(
                Severity.WARNING,
                f"Car '{name}' is changing lanes. UMLSL-Sim starts it in the middle of its current lane.",
            ))

        goal = None
        if segment is not None:
            placed.append(_PlacedCar(name, road, direction, lane, rear, size, positive, segment))
            goal = _goal(car, road, direction, lane, segment, road_by_uid, network)
            if goal is None:
                issues.append(SimulationIssue(
                    Severity.WARNING,
                    f"The turn of car '{name}' cannot be expressed in UMLSL-Sim. It gets a random goal instead.",
                ))

        car_speed = max(0, round(speed))
        external: dict[str, Any] = {
            "type": "NPC",
            "name": name,
            "start": {"road": road.name, "direction": direction, "lane": lane, "position": rear},
            "color": _color(car.get("color", "green")),
            "size": size,
            "speed": car_speed,
            "max_speed": max(car_speed, round(max_speed)) if max_speed is not None else car_speed,
        }
        if goal is not None:
            external["first_goal"] = goal
        external_cars.append(external)

    issues += _check_overlaps(placed)

    if editor_roads and len(external_cars) > network.capacity:
        issues.append(SimulationIssue(
            Severity.ERROR,
            f"The scenario has {len(external_cars)} cars but only {network.capacity} lane segments. "
            f"UMLSL-Sim needs a lane segment for each car.",
        ))

    payload = {
        "name": scenario_key.upper(),
        "scenario_name": scenario_key.lower(),
        "players": len(external_cars),
        "roads": [r.to_payload() for r in network.roads],
        "cars": external_cars,
    }
    return SimulatorScenario(payload=payload, issues=issues)


def _goal(
        car: dict[str, Any],
        road: SimRoad,
        direction: str,
        lane: int,
        segment: int,
        road_by_uid: dict[str, SimRoad],
        network: _Network,
) -> dict[str, Any] | None:
    """
    The simulator goal that reproduces the car's intent at its next crossing.

    Straight on: the next lane segment of its own lane, past the next crossing.
    Turning: the first lane segment of the target lane past the crossing with
    the car's road. ``None`` if the intent cannot be expressed.
    """
    turn = car.get("next_turn")
    if not turn or turn.get("direction") in (None, "STRAIGHT"):
        segments = network.segments_along(road)
        step = 1 if int(car.get("lane_index", 0)) >= 0 else -1
        target = segments[(segment + step) % len(segments)]
        return {"road": road.name, "direction": direction, "lane": lane, "position": _midpoint(target)}

    target_lane = turn.get("target_lane") or {}
    target_road = road_by_uid.get(target_lane.get("road_uid"))
    if target_road is None or target_road.horizontal == road.horizontal:
        return None
    target_index = int(target_lane.get("lane_index", 0))
    target_direction, target_number = map_lane(target_road, target_index)
    lanes = target_road.right if target_direction == "right" else target_road.left
    target_segments = network.segments_along(target_road)
    if not 0 <= target_number < lanes or not target_segments:
        return None

    # The car's road crosses the target road at [road.top, road.bottom]; the
    # goal is the first segment past it in the target lane's direction.
    if target_index >= 0:
        chosen = next((s for s in target_segments if s[0] >= road.bottom), target_segments[0])
    else:
        chosen = next((s for s in reversed(target_segments) if s[1] <= road.top), target_segments[-1])
    return {
        "road": target_road.name,
        "direction": target_direction,
        "lane": target_number,
        "position": _midpoint(chosen),
    }


def _check_overlaps(placed: list[_PlacedCar]) -> list[SimulationIssue]:
    issues = []
    for i, a in enumerate(placed):
        for b in placed[i + 1:]:
            if (a.road is b.road and a.direction == b.direction and a.lane == b.lane
                    and a.segment == b.segment):
                a_low, a_high = a.footprint()
                b_low, b_high = b.footprint()
                if a_low < b_high and b_low < a_high:
                    issues.append(SimulationIssue(
                        Severity.ERROR,
                        f"Cars '{a.name}' and '{b.name}' overlap. UMLSL-Sim cannot start with overlapping cars.",
                    ))
    return issues


# ----------------------------------------------------------------------
# Simulator -> editor: the inverses of the mapping above
# ----------------------------------------------------------------------

def sim_road(payload: dict[str, Any]) -> SimRoad:
    """A road of the interchange payload."""
    return SimRoad(
        name=str(payload.get("name", "")),
        horizontal=bool(payload.get("horizontal")),
        top=int(payload.get("top", 0)),
        right=int(payload.get("right", 0)),
        left=int(payload.get("left", 0)),
    )


def unmap_road(road: SimRoad) -> dict[str, Any]:
    """
    The editor fields of a simulator road. Inverse of ``map_road``.

    Returns:
        ``orientation``, ``position``, ``number_of_forward_lanes`` and
        ``number_of_backward_lanes``, as ``to_dict`` writes them.
    """
    forward, backward = (road.right, road.left) if road.horizontal else (road.left, road.right)
    return {
        "orientation": "HORIZONTAL" if road.horizontal else "VERTICAL",
        "position": road.top / UNIT - across_offset(road.horizontal) + road.right,
        "number_of_forward_lanes": forward,
        "number_of_backward_lanes": backward,
    }


def unmap_position(horizontal: bool, position: float) -> float:
    """Simulator axis coordinate on a road -> editor ``position_on_lane``."""
    return position / UNIT - along_offset(horizontal)


def _drives_positive(road: SimRoad, direction: str) -> bool:
    """Whether a car in this lane group drives towards +x / +y (editor lane index >= 0)."""
    return (direction == "right") == road.horizontal


def _heading(road: SimRoad, positive: bool) -> tuple[int, int]:
    sign = 1 if positive else -1
    return (sign, 0) if road.horizontal else (0, sign)


@dataclass(frozen=True)
class SimTurn:
    """An editor turn intent, found in simulator terms."""

    direction: str
    """``"LEFT"`` or ``"RIGHT"``, as ``TurnDirection`` names them."""
    road: str
    """Name of the road the car turns into."""
    lane_index: int
    """Editor lane index of the target lane on that road."""


def unmap_turn(start: dict[str, Any], target: dict[str, Any] | None, network: _Network) -> SimTurn | None:
    """
    The editor turn intent of a car whose route next enters ``target``. Inverse of ``_goal``.

    The editor only knows the turn at the next crossing, and stores "straight
    on" as no turn at all. So a turn is found only when ``target`` lies in the
    first lane segment past the car's next crossing, on the road that crosses
    there. That is where ``_goal`` puts the goal of a turning car. Like the
    editor, only the first road of the crossing counts when roads touch, and
    the canvas edges do not join, because the editor's canvas does not wrap.

    Args:
        start: The car's ``start`` position reference.
        target: A position reference on the lane the car enters after its next
            crossing, or its ``first_goal``.
        network: All roads of the payload.

    Returns:
        The turn, or ``None`` if the car goes straight on or the turn is not at
        its next crossing.
    """
    if not target:
        return None
    by_name = {r.name: r for r in network.roads}
    road = by_name.get(start.get("road"))
    target_road = by_name.get(target.get("road"))
    if road is None or target_road is None or target_road.horizontal == road.horizontal:
        return None

    positive = _drives_positive(road, str(start.get("direction", "right")))
    segments = network.segments_along(road)
    segment = _segment_index(segments, float(start.get("position", 0)))
    if segment is None:
        return None
    low, high = segments[segment]
    crossing = next((r for r in network.roads if r.horizontal != road.horizontal
                     and (r.top == high if positive else r.bottom == low)), None)
    if crossing is not target_road:
        return None

    target_direction = str(target.get("direction", "right"))
    target_number = int(target.get("lane", 0))
    lanes = target_road.right if target_direction == "right" else target_road.left
    target_segments = network.segments_along(target_road)
    if not 0 <= target_number < lanes or not target_segments:
        return None
    target_positive = _drives_positive(target_road, target_direction)
    if target_positive:
        chosen = next((s for s in target_segments if s[0] >= road.bottom), target_segments[0])
    else:
        chosen = next((s for s in reversed(target_segments) if s[1] <= road.top), target_segments[-1])
    if not chosen[0] <= float(target.get("position", 0)) <= chosen[1]:
        return None

    hx, hy = _heading(road, positive)
    turn = "LEFT" if _heading(target_road, target_positive) == (-hy, hx) else "RIGHT"
    return SimTurn(
        direction=turn,
        road=target_road.name,
        lane_index=unmap_lane(target_road.horizontal, target_road.right, target_direction, target_number),
    )


def _road_key(road: SimRoad) -> tuple[str, bool, int, int, int]:
    return road.name, road.horizontal, road.top, road.right, road.left


def removable_border_roads(roads: list[SimRoad], used: set[str]) -> set[str]:
    """
    Names of the roads the editor can leave out, because exporting adds them again.

    A road qualifies when no car uses it and it is exactly, name included, a
    border road that ``border_roads`` would add for the roads that stay. Then
    Editor -> Sim -> Editor gives back the original roads, and exporting again
    gives back the original simulator roads.

    Args:
        roads: All roads of the payload.
        used: Names of the roads a car starts on or turns into.
    """
    removable = {r.name for r in roads if r.name not in used}
    while True:
        kept = [r for r in roads if r.name not in removable]
        added = {_road_key(r) for r in border_roads(kept)}
        still = {r.name for r in roads if r.name in removable and _road_key(r) in added}
        if still == removable:
            return removable
        removable = still
