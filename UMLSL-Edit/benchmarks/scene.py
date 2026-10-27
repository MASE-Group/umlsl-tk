"""The traffic snapshot the model-checker benchmarks decide their formulas on.

A grid of eight roads -- four horizontal, four vertical, 60 units apart, each
with two lanes per direction -- holding 40 cars. The ego car E drives east on
the inner road H1, 15 units before its crossing with V2, so that its virtual
view (about 29 units long with the editor's default braking deceleration of 8
and maximum speed of 15) spans three virtual lanes and runs into that
crossing.

The number of cars in E's view is set by where the other cars are put: `k - 1`
of them are placed on E's road, inside the view, according to a layout, and the
rest are parked on the outer roads, far outside it, so that the scenario holds
the same number of cars whatever `k` is. A car counts as being in the view when
its reservation or claim overlaps it -- exactly the set the model checker's
quantifiers range over (`ParsedUMLSLQuery._evaluate_parallel_virtual_lane`).
E is one of them.

The snapshot is written in the editor's native format and loaded with
`TrafficSnapshotModel.from_dict`, the path the editor's evaluation worker takes
(`umlsl_edit.query.evaluation_worker`) before it parses and evaluates a
formula. Building it through the editor's commands gives the same snapshot but
is an order of magnitude slower, since every command re-validates the whole
scene.
"""

import random
import uuid

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.environment.view_coordinate_translation import translate_into_ego_coordinates

DEFAULT_TOTAL_CARS = 40
BRAKING_DECELERATION = 8.0      # the editor's defaults (application_controller.py)
MAX_SPEED = 15.0

ROAD_POSITIONS = [0.0, 60.0, 120.0, 180.0]
LANES_PER_DIRECTION = 2
EGO_ROAD = "H1"
EGO_LANE = 0
EGO_POSITION = 108.0
CAR_SPEED = 5.0
CAR_LENGTH = 1.0

# E's lane segment on H1 runs from 62 to 118, where the crossing with V2 begins, and E's view covers
# [93.9, 123.0] on lanes 1, 0 and -1. Cars are placed within WINDOW, so that their reservations lie in
# the view, and on lane 0 they keep clear of E and its reservation.
VIEW_LANES = (1, -1, 0)
WINDOW = (94.5, 116.0)
EGO_SPAN = (106.0, 111.0)
MIN_GAP = 3.0                   # rear to rear on one lane: a car's length plus its reservation (2.5625)


def uniform_layout(n: int) -> list:
    """`n` cars at uniform spacing, dealt round-robin over the three lanes of E's view."""
    lanes = [VIEW_LANES[i % len(VIEW_LANES)] for i in range(n)]
    placements = []
    for lane in VIEW_LANES:
        count = lanes.count(lane)
        low, high = WINDOW
        if lane == 0:
            high = EGO_SPAN[0] - MIN_GAP        # E's own lane: only the stretch behind E
        step = (high - low) / max(count, 1)
        placements += [(lane, round(low + step * (i + 0.5), 3)) for i in range(count)]
    return placements


def random_layout(n: int, seed: int) -> list:
    """`n` cars at random positions in E's view, at least MIN_GAP apart on each lane."""
    rng = random.Random(seed)
    taken = {lane: [] for lane in VIEW_LANES}
    placements = []
    while len(placements) < n:
        lane = rng.choice(VIEW_LANES)
        position = round(rng.uniform(*WINDOW), 3)
        if lane == 0 and EGO_SPAN[0] - MIN_GAP < position < EGO_SPAN[1]:
            continue
        if any(abs(position - other) < MIN_GAP for other in taken[lane]):
            continue
        taken[lane].append(position)
        placements.append((lane, position))
    return placements


def layout(name: str, n: int) -> list:
    """Placements of the `n` cars near E: 'uniform', or 'random<i>' for the i-th random layout."""
    if name == "uniform":
        return uniform_layout(n)
    if name.startswith("random"):
        # distinct densities never share a layout
        return random_layout(n, seed=1000 * int(name[len("random"):]) + n)
    raise ValueError(f"unknown layout {name!r}")


def snapshot_dict(near: list, total_cars: int = DEFAULT_TOTAL_CARS) -> dict:
    """The snapshot in the editor's native format, with E, the cars in `near`, and parked cars."""
    roads = {}
    for i, position in enumerate(ROAD_POSITIONS):
        for orientation, prefix in (("HORIZONTAL", "H"), ("VERTICAL", "V")):
            roads[f"{prefix}{i}"] = {
                "uid": str(uuid.uuid4()), "name": f"{prefix}{i}", "orientation": orientation,
                "position": position, "number_of_forward_lanes": LANES_PER_DIRECTION,
                "number_of_backward_lanes": LANES_PER_DIRECTION,
            }

    cars = []

    def add(name: str, road: str, lane: int, position: float) -> None:
        cars.append({
            "uid": str(uuid.uuid4()), "name": name, "road_uid": roads[road]["uid"],
            "lane_index": lane, "position_on_lane": position, "transition": 0.0,
            "speed": CAR_SPEED, "length": CAR_LENGTH, "color": "#ff0000",
            "acceleration": 0.0, "next_turn": None,
        })

    add("E", EGO_ROAD, EGO_LANE, EGO_POSITION)
    for i, (lane, position) in enumerate(near):
        add(f"N{i}", EGO_ROAD, lane, position)

    # parked between the first two crossings of the outer roads, far from E
    parking = [(road, lane, 12.0 + 8.0 * slot)
               for road in ("H3", "V3", "H0", "V0")
               for lane in (0, 1, -1, -2)
               for slot in range(5)]
    parked = total_cars - 1 - len(near)
    if not 0 <= parked <= len(parking):
        raise ValueError(f"cannot park {parked} cars ({len(parking)} spaces)")
    for i, (road, lane, position) in enumerate(parking[:parked]):
        add(f"P{i}", road, lane, position)

    return {"meta": {"version": 2}, "roads": list(roads.values()), "cars": cars, "queries": []}


def build(near: list, total_cars: int = DEFAULT_TOTAL_CARS):
    """Load the snapshot; returns (snapshot, E)."""
    settings = SettingsModel(braking_acceleration=BRAKING_DECELERATION, max_speed=MAX_SPEED)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    TrafficSnapshotModel.from_dict(snapshot_dict(near, total_cars), snapshot, snapshot, settings)
    ego = next(car for car in snapshot.get_cars().values() if car.name == "E")
    return snapshot, ego


def cars_in_view(snapshot, ego) -> list:
    """Names of the cars whose reservation or claim overlaps E's view, over all its parallel views."""
    horizon = ego.environment.horizon
    seen = set()
    for parallel_lanes in ego.environment.parallel_virtual_lanes:
        translation = translate_into_ego_coordinates(snapshot, ego, horizon, parallel_lanes)
        for uid in translation.reserved:
            for occupied in (translation.reserved[uid], translation.claimed[uid]):
                for interval in occupied.values():
                    overlap = interval.intersection(horizon)
                    if overlap is not None and overlap.length() > 0:
                        seen.add(uid)
    cars = snapshot.get_cars()
    return sorted(cars[uid].name for uid in seen)
