import math
import re
import uuid
from typing import Any, Final

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.query.lexer import TokenType
from umlsl_edit.services.simulator_scenario import (
    HEIGHT_LANES,
    UNIT,
    WIDTH_LANES,
    _Network,
    build_simulator_scenario,
    removable_border_roads,
    sim_road,
    unmap_lane,
    unmap_position,
    unmap_road,
    unmap_turn,
)


class ExternalPersistenceService:
    """
    Handles saving/loading JSON payloads to and from Simulator.

    The coordinate, unit and lane-order mapping between the two tools is
    described, and implemented, in ``umlsl_edit.services.simulator_scenario``.
    Writing goes through ``build_simulator_scenario``; reading inverts the same
    mapping here.
    """

    HEIGHT_SIMULATOR: Final[int] = HEIGHT_LANES
    WIDTH_SIMULATOR: Final[int] = WIDTH_LANES
    UNIT_SIZE: Final[int] = UNIT

    @staticmethod
    def is_external_payload(data: Any) -> bool:
        """
        Report whether a parsed JSON payload is in the UMLSL-Sim interchange
        format rather than the editor's native format.

        The native format always carries a "meta" block and describes roads by
        "orientation"; the interchange format carries "scenario_name"/"players"
        and describes roads by "horizontal".
        """
        if not isinstance(data, dict) or "meta" in data:
            return False
        if "scenario_name" in data or "players" in data:
            return True
        roads = data.get("roads")
        return (
            isinstance(roads, list)
            and len(roads) > 0
            and isinstance(roads[0], dict)
            and "horizontal" in roads[0]
        )

    @staticmethod
    def serialize(
            snapshot: TrafficSnapshotModel,
            filename: str,
            max_speed: float | None = None,
    ) -> dict[str, Any]:
        """
        Serialize snapshot to the external JSON format (e.g., 'two_crossings_predefined').

        This returns the payload only. Use
        ``simulator_scenario.build_simulator_scenario`` to also learn whether
        UMLSL-Sim can run it.
        """
        return build_simulator_scenario(snapshot.to_dict(), filename, max_speed).payload

    @staticmethod
    def deserialize(
            data: dict[str, Any],
            traffic_snapshot_writer: TrafficSnapshotWriter,
            traffic_snapshot_reader: TrafficSnapshotReader,
            settings_model: SettingsModel
    ) -> list[str]:
        """
        Populate snapshot from the external JSON format.

        Each step inverts the matching step of ``build_simulator_scenario``:

        * Roads and lanes go back through ``unmap_road`` and ``unmap_lane``.
        * A car's turn intent comes from ``unmap_turn``. The target is the
          car's ``next_lane``, which UMLSL-Sim writes from the car's planned
          route. Without one, the target is its ``first_goal``, which is where
          the export puts the goal of a turning car. Goals beyond the next
          crossing cannot be expressed, so those cars go straight on.
        * Border roads that no car uses are left out when exporting would add
          exactly the same road again (``removable_border_roads``).

        Three rules of the editor have no counterpart in UMLSL-Sim, so the
        data is adjusted to fit them:

        * A car whose rear lies exactly on the edge of a crossing moves 1 px
          into its lane segment, because the editor counts the edge as part of
          the crossing.
        * A car or road name that contains a UMLSL token is upper-cased (see
          ``_make_names_valid``).
        * The global maximum speed grows until every car's braking distance
          plus its length fits in the global braking distance (see
          ``_max_speed_for``).

        Returns:
            One sentence for each kind of change the user should know about:
            renamed cars or roads, a higher global maximum speed, and cars
            whose planned move the editor cannot show. Empty if none applies.
        """

        ext_roads = data.get("roads", [])
        ext_cars = data.get("cars", [])
        original_max_speed = settings_model.max_speed

        sim_roads = [sim_road(r) for r in ext_roads]
        sim_road_by_name = {r.name: r for r in sim_roads}
        network = _Network(sim_roads)

        def start_of(car: dict[str, Any]) -> dict[str, Any]:
            start = dict(car.get("start", {}))
            # "down" is an old name for the "right" lane group.
            start["direction"] = "right" if start.get("direction", "right") in ("right", "down") else "left"
            return start

        turns = [
            unmap_turn(start_of(c), c["next_lane"] if "next_lane" in c else c.get("first_goal"), network)
            for c in ext_cars
        ]
        used = {start_of(c).get("road", "") for c in ext_cars} | {t.road for t in turns if t is not None}
        left_out = removable_border_roads(sim_roads, used)

        internal_roads = []
        road_name_to_uid = {}
        for road in sim_roads:
            if road.name in left_out:
                continue
            road_uid = str(uuid.uuid4())
            road_name_to_uid[road.name] = road_uid
            internal_roads.append({"uid": road_uid, "name": road.name, **unmap_road(road)})

        internal_cars = []
        for idx, (c, turn) in enumerate(zip(ext_cars, turns)):
            start = start_of(c)
            road_name = start.get("road", "")
            road_uid = road_name_to_uid.get(road_name, "")
            road = sim_road_by_name.get(road_name)
            horizontal = road.horizontal if road is not None else False

            lane_index = unmap_lane(
                horizontal,
                road.right if road is not None else 0,
                start["direction"],
                int(start.get("lane", 0)),
            )
            position = float(start.get("position", 0.0))
            if road is not None:
                position = _off_crossing_edge(network.segments_along(road), position)
            position_on_lane = unmap_position(horizontal, position)

            next_turn = None
            if turn is not None:
                next_turn = {
                    "direction": turn.direction,
                    "target_lane": {"road_uid": road_name_to_uid[turn.road], "lane_index": turn.lane_index},
                }

            # Reverse color calculation: RGB tuple back to hex string
            ext_color = c.get("color", (173, 216, 230))
            if isinstance(ext_color, (list, tuple)) and len(ext_color) >= 3:
                color = "#{:02x}{:02x}{:02x}".format(int(ext_color[0]), int(ext_color[1]), int(ext_color[2]))
            else:
                color = str(ext_color)

            # Reverse length calculation: size = length * 40
            size = c.get("size", ExternalPersistenceService.UNIT_SIZE)
            length = size / ExternalPersistenceService.UNIT_SIZE

            internal_cars.append({
                "uid": str(uuid.uuid4()),
                "name": c.get("name", f"C{idx+1}"),
                "road_uid": road_uid,
                "lane_index": lane_index,
                "position_on_lane": position_on_lane,
                "transition": 0.0,
                "speed": c.get("speed", 0.0),
                "length": length,
                "color": color,
                "acceleration": 1.0,
                "next_turn": next_turn,
            })
            if c.get("max_speed", 0.0) > settings_model.max_speed:
                settings_model.max_speed = c.get("max_speed")

        # Checked before renaming, so the notes use the names from UMLSL-Sim.
        straight_instead = [
            str(c.get("name", "")) for c, turn in zip(ext_cars, turns)
            if turn is None and "next_lane" in c and _lane_of(c["next_lane"]) != _lane_of(start_of(c))
        ]
        renamed = _make_names_valid(internal_roads + internal_cars)
        required = _max_speed_for(internal_cars, settings_model.braking_acceleration)
        if required > settings_model.max_speed:
            settings_model.max_speed = required

        TrafficSnapshotModel.from_dict(
            {"roads": internal_roads, "cars": internal_cars},
            traffic_snapshot_writer,
            traffic_snapshot_reader,
            settings_model
        )

        notes = []
        if renamed:
            notes.append("Names that contain a UMLSL token were changed: "
                         + ", ".join(f"{old} → {new}" for old, new in renamed) + ".")
        if settings_model.max_speed > original_max_speed:
            notes.append(f"The global maximum speed went up from {original_max_speed:g} to "
                         f"{settings_model.max_speed:g}, so that every car's braking distance fits.")
        if straight_instead:
            notes.append("UMLSL-Edit cannot show the next move of " + ", ".join(straight_instead)
                         + " as a turn at the next crossing (for example a U-turn, a lane change in a"
                         " crossing, or a route across the canvas edge), so they go straight on.")
        return notes


EDGE_NUDGE: Final[int] = 1
"""How far, in simulator pixels, a car on the edge of a crossing moves into its lane."""


def _off_crossing_edge(segments: list[tuple[int, int]], position: float) -> float:
    """
    ``position`` moved ``EDGE_NUDGE`` into its lane segment if it lies on an end of one.

    UMLSL-Sim counts both ends of a lane segment as part of it, while the editor
    puts them in the neighbouring crossing and refuses a car there.
    """
    for low, high in segments:
        if position == low:
            return position + EDGE_NUDGE
        if position == high:
            return position - EDGE_NUDGE
    return position


def _lane_of(ref: dict[str, Any]) -> tuple[Any, Any, int]:
    return ref.get("road"), ref.get("direction"), int(ref.get("lane", 0))


def _has_token(name: str) -> bool:
    return any(token.value in name for token in TokenType)


def _make_names_valid(entities: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """
    Rename, in place, every road and car whose name the editor refuses.

    The editor refuses names that contain a UMLSL token anywhere, such as the
    "re" in "Green". Every word token is lower case, so such a name is
    upper-cased: "Green" becomes "GREEN". Characters other than letters, digits
    and "_" become "_". A name that is still taken, or still contains a token,
    gets a numbered suffix or, last, a generic name. Names that the editor
    accepts are kept as they are.

    Returns:
        The (old, new) pairs of every renamed entity.
    """
    renamed = []
    taken = {e["name"] for e in entities if not _has_token(e["name"])}
    for index, entity in enumerate(entities, start=1):
        name = entity["name"]
        if not _has_token(name):
            continue
        base = re.sub(r"[^0-9A-Za-z_]+", "_", name).upper().strip("_")
        if not base or _has_token(base):
            base = f"N{index}"
        candidate, n = base, 2
        while candidate in taken:
            candidate, n = f"{base}_{n}", n + 1
        taken.add(candidate)
        entity["name"] = candidate
        renamed.append((name, candidate))
    return renamed


def _max_speed_for(cars: list[dict[str, Any]], braking_acceleration: float) -> float:
    """
    The smallest whole maximum speed at which the editor accepts every car.

    The editor requires ``speed² / (2·a) + length <= max_speed² / (2·a)``, so a
    car that drives at the maximum speed never fits. UMLSL-Sim has no such
    rule. Returns 0 when there are no cars.
    """
    required = 0
    for car in cars:
        speed, length = float(car["speed"]), float(car["length"])
        needed = math.ceil(math.sqrt(speed * speed + 2.0 * braking_acceleration * length))
        # Guard against rounding: the editor compares the unrounded values.
        while speed * speed / (2.0 * braking_acceleration) + length > needed * needed / (2.0 * braking_acceleration):
            needed += 1
        required = max(required, needed)
    return required
