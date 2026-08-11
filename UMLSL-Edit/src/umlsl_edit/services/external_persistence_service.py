import uuid
from typing import Any, Final

from PIL import ImageColor

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


class ExternalPersistenceService:
    """
    Handles saving/loading JSON payloads to and from Simulator.

                            Editor          vs             Simulator

                                                        right   left
    lane indexing :    -3 -2 -1 | 0 1 2                 0 1 2 | 0 1 2
                    -3          ^                   2   ^
                    -2          |            left   1   |
                    -1                              0
                -> ---                             ---
                    0                               2
                    1                        right  1
                    2                            -> 0

                (Arrows show the saved position of the road.)

    Unit/Lane size: 1 unit = 1;                        1 unit = 40
    canvas size:    "infinite", but view is limited;   height: 24 lanes, width: 40 lanes
    Origin:         center of screen, draggable;       bottom left
    Colors:         hex, "lightblue";                  rgb
    Max Speed:      one max speed for all;             one per car
    Turning:        explicitly through turn intend;    implicitly through goal
    """

    HEIGHT_SIMULATOR:Final[int] = 24
    WIDTH_SIMULATOR:Final[int] = 40
    UNIT_SIZE:Final[int] = 40

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
    ) -> dict[str, Any]:
        """
        Serialize snapshot to the external JSON format (e.g., 'two_crossings_predefined').
        """
        snapshot_data = snapshot.to_dict()

        internal_roads = snapshot_data.get("roads", [])
        internal_cars = snapshot_data.get("cars", [])

        external_roads = []

        # saving these for easy lookup when serializing cars
        road_uid_to_name = {}
        road_uid_to_orientation = {}
        road_uid_to_right_lanes = {}
        road_uid_to_left_lanes = {}
        road_uid_to_position = {}

        for r in internal_roads:
            road_name = r.get("name", "unknown")
            road_uid_to_name[r.get("uid")] = road_name

            orientation = r.get("orientation") == "HORIZONTAL"
            road_uid_to_orientation[r.get("uid")] = orientation

            # offsetting position so that 0,0 is in the bottom left corner and not in the center
            offset = ExternalPersistenceService.HEIGHT_SIMULATOR/2 if orientation else ExternalPersistenceService.WIDTH_SIMULATOR/2
            top = (r.get("position", 0.0) + offset)

            right = r.get("number_of_forward_lanes", 0)
            left = r.get("number_of_backward_lanes", 0)

            road_uid_to_right_lanes[r.get("uid")] = right
            road_uid_to_left_lanes[r.get("uid")] = left

            # adjusting position so it is the minimum x/y coordinate and not the center of the road
            if orientation:
                top -= right
            else:
                (right, left) = (left, right)
                top -= left

            road_uid_to_position[r.get("uid")] = top

            # scaling position so one lane is 40 units wide
            top *= ExternalPersistenceService.UNIT_SIZE


            external_roads.append(
                {
                    "name": road_name,
                    "horizontal": orientation,
                    "top": top,
                    "right": r.get("number_of_forward_lanes", 0),
                    "left": r.get("number_of_backward_lanes", 0),
                }
            )

        if not any(r.get("name") in ["bottom", "right", "top", "left"] for r in external_roads):
            # if no border roads are present, add them. Needed in simulator.
            border_roads = [
                {"name": "bottom", "horizontal": True, "top": 0, "right": 1, "left": 0},
                {"name": "right", "horizontal": False, "top": (ExternalPersistenceService.WIDTH_SIMULATOR-1)*ExternalPersistenceService.UNIT_SIZE, "right": 0, "left": 1},
                {"name": "top", "horizontal": True, "top": (ExternalPersistenceService.HEIGHT_SIMULATOR-1)*ExternalPersistenceService.UNIT_SIZE, "right": 0, "left": 1},
                {"name": "left", "horizontal": False, "top": 0, "right": 1, "left": 0},
            ]
            external_roads.extend(border_roads)

        external_cars = []
        # A snapshot may legitimately contain no cars at all, so max() needs a default.
        space_after_crossing = max(
            (c.get("length", 1.0) for c in internal_cars), default=1.0
        ) + 0.01

        for c in internal_cars:
            road_uid = c.get("road_uid")
            road_name = road_uid_to_name.get(road_uid, "unknown")

            lane_index = c.get("lane_index", 0)
            lane = lane_index if lane_index >= 0 else abs(lane_index) - 1

            offset = ExternalPersistenceService.WIDTH_SIMULATOR/2 if road_uid_to_orientation.get(road_uid) else ExternalPersistenceService.HEIGHT_SIMULATOR/2
            position = (c.get("position_on_lane", 0.0) + offset) * ExternalPersistenceService.UNIT_SIZE

            # Determine direction based on lane_index (negative index indicates backward/left lane)
            direction = "right" if c.get("lane_index", 0) >= 0 else "left"
            if not road_uid_to_orientation.get(road_uid):
                direction = "right" if direction == "left" else "left"

            # switch lane index for roads with direction "right" (so lane 0 to lane 2 becomes lane 2 to lane 0)
            if direction == "right":
                # get the number of right lanes for the road that this car is on
                num_of_right_lanes = road_uid_to_right_lanes.get(road_uid)
                # switch lane index for roads with direction "right"
                lane = num_of_right_lanes - lane - 1


            start = {
                "road": road_name,
                "direction": direction,
                "lane": lane,
                "position": position
            }

            color = ImageColor.getrgb(c.get("color", "green"))

            # turn_intend -> goal. So goal is the position right after the next turn
            next_turn = c.get("next_turn")

            if next_turn and next_turn.get("direction", 2)!= 2:
                target_lane = next_turn.get("target_lane", {})
                target_road_uid = target_lane.get("road_uid")
                target_lane_index = target_lane.get("lane_index", 0)

                turn_direction = next_turn.get("direction")

                after_turn_car_direction = "right" if target_lane_index >= 0 else "left"
                if not road_uid_to_orientation.get(target_road_uid):
                    after_turn_car_direction = "right" if after_turn_car_direction == "left" else "left"

                turn_road_name = road_uid_to_name.get(target_road_uid, "unknown")

                #same lane index conversion like the car lane
                turn_lane = target_lane_index if target_lane_index >= 0 else abs(target_lane_index) - 1


                if after_turn_car_direction == "right":
                    num_of_right_lanes = road_uid_to_right_lanes.get(target_road_uid)
                    turn_lane = num_of_right_lanes - turn_lane - 1

                # adding the width of the road to the minimum x/y pos of the road to get the correct position after the turn
                # but only if the car turns to the far side of the road
                # also adding a very small offset after the turn so the position is in the correct segment

                # road_uid_to_orientation holds booleans (True == horizontal), not the
                # "HORIZONTAL"/"VERTICAL" strings of the native format.
                cars_is_horizontal = bool(road_uid_to_orientation.get(road_uid))
                car_is_on_positive_axis_lane = (cars_is_horizontal and direction == "right") or (not cars_is_horizontal and direction == "left")

                if (car_is_on_positive_axis_lane and turn_direction == "RIGHT") or (not car_is_on_positive_axis_lane and turn_direction == "LEFT"):
                    turn_offset =  road_uid_to_right_lanes.get(road_uid, 0) + road_uid_to_left_lanes.get(road_uid, 0) + space_after_crossing
                else:
                    turn_offset = -space_after_crossing


                # The position right after the next turn defaults to the start of the lane (position_on_lane = 0.0)
                turn_position = road_uid_to_position.get(road_uid, 0) + turn_offset
                turn_position *= ExternalPersistenceService.UNIT_SIZE
            else:
                # If straight, use current lane and direction but offset the position so it is over the next crossing
                turn_road_name = road_name
                after_turn_car_direction = direction
                turn_lane = lane

                car_orientation = road_uid_to_orientation.get(road_uid)

                roads_in_other_direction = {
                    uid: is_horizontal
                    for uid, is_horizontal in road_uid_to_orientation.items()
                    if is_horizontal != car_orientation
                }

                #find next road in other direction
                car_drives_in_positive_direction = c.get("lane_index", 0) >= 0
                next_road_uid = None
                cpos = position/ExternalPersistenceService.UNIT_SIZE

                #finds the next road crossing in the positive direction and calculates the position after the turn with the position of the road + the width of the road + a small offset
                if car_drives_in_positive_direction:
                    next_road_position = float('inf')
                    for uid in roads_in_other_direction:
                        pos = road_uid_to_position.get(uid)
                        if pos > cpos and pos < next_road_position:
                            next_road_position = pos
                            next_road_uid = uid

                    # if no road found, use current position as crossing point
                    if not next_road_uid:
                        pos_after_crossing = cpos
                    else:
                        pos_after_crossing = next_road_position + road_uid_to_left_lanes.get(next_road_uid) + road_uid_to_right_lanes.get(next_road_uid) + space_after_crossing

                # find the next road crossing in the negative direction and calculate the position after the turn with the position of the road - a small offset
                else:
                    next_road_position = float('-inf')
                    for uid in roads_in_other_direction:
                        pos = road_uid_to_position.get(uid) - road_uid_to_left_lanes.get(uid) - road_uid_to_right_lanes.get(uid)
                        if pos < cpos and road_uid_to_position.get(uid) > next_road_position:
                            next_road_position = road_uid_to_position.get(uid)
                            next_road_uid = uid

                    # if no road found, use current position as crossing point
                    if not next_road_uid:
                        pos_after_crossing = cpos
                    else:
                        pos_after_crossing = next_road_position - space_after_crossing

                turn_position = pos_after_crossing * ExternalPersistenceService.UNIT_SIZE

            turn_goal = {
                "road": turn_road_name,
                "direction": after_turn_car_direction,
                "lane": turn_lane,
                "position": turn_position
            }


            external_cars.append({
                "type": "NPC",
                "name": c.get("name", ""),
                "start": start,
                "first_goal": turn_goal,
                "color": color,
                "size": c.get("length", 1.0)*ExternalPersistenceService.UNIT_SIZE,
                "speed": c.get("speed", 0.0),
                "max_speed": c.get("speed", 0.0),
            })

        return {
            "name": filename.upper(),
            "scenario_name": filename.lower(), #TODO: Remove scenario_name
            "players": len(external_cars),
            "roads": external_roads,
            "cars": external_cars
        }

    @staticmethod
    def deserialize(
            data: dict[str, Any],
            traffic_snapshot_writer: TrafficSnapshotWriter,
            traffic_snapshot_reader: TrafficSnapshotReader,
            settings_model: SettingsModel
    ) -> None:
        """
        Populate snapshot from the external JSON format.
        """

        ext_roads = data.get("roads", [])
        ext_cars = data.get("cars", [])

        internal_roads = []
        road_name_to_uid = {}
        road_uid_to_horizontal = {}

        for r in ext_roads:
            road_uid = str(uuid.uuid4())
            road_name = r.get("name", "")
            road_name_to_uid[road_name] = road_uid

            horizontal = bool(r.get("horizontal"))
            road_uid_to_horizontal[road_uid] = horizontal

            # Reverse road position calculation: top = (position + offset) * 40
            road_offset = ExternalPersistenceService.HEIGHT_SIMULATOR/2 if horizontal else ExternalPersistenceService.WIDTH_SIMULATOR/2
            position = (r.get("top", 0.0) / ExternalPersistenceService.UNIT_SIZE) - road_offset

            number_of_forward_lanes = r.get("right", 0)
            number_of_backward_lanes = r.get("left", 0)

            # Offset position because position of road is middle lane and not minimum x/y coordinate
            if horizontal:
                position += number_of_forward_lanes
            else:
                (number_of_forward_lanes, number_of_backward_lanes) = (number_of_backward_lanes, number_of_forward_lanes)
                position += number_of_backward_lanes

            internal_roads.append({
                "uid": road_uid,
                "name": road_name,
                "orientation": "HORIZONTAL" if horizontal else "VERTICAL",
                "position": position,
                "number_of_forward_lanes": number_of_forward_lanes,
                "number_of_backward_lanes": number_of_backward_lanes
            })

        internal_cars = []
        for idx, c in enumerate(ext_cars):
            start = c.get("start", {})
            road_name = start.get("road", "")
            direction = start.get("direction", "right")
            lane_val = start.get("lane", 0)
            road_uid = road_name_to_uid.get(road_name, "")

            # Reverse lane_index calculation
            if (direction in ["right", "down"] and road_uid_to_horizontal.get(road_uid)) or (direction in ["left", "up"] and not road_uid_to_horizontal.get(road_uid)):
                lane_index = lane_val
            else:
                lane_index = -(lane_val + 1)

            # Reverse car position calculation: position = (position_on_lane + offset) * 40
            horizontal = road_uid_to_horizontal.get(road_uid, False)
            car_offset = ExternalPersistenceService.WIDTH_SIMULATOR/2 if horizontal else ExternalPersistenceService.HEIGHT_SIMULATOR/2
            ext_position = start.get("position", 0.0)
            position_on_lane = (ext_position / ExternalPersistenceService.UNIT_SIZE) - car_offset

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
                "next_turn": None
            })
            if c.get("max_speed", 0.0) > settings_model.max_speed:
                settings_model.max_speed = c.get("max_speed")

        TrafficSnapshotModel.from_dict(
            {"roads": internal_roads, "cars": internal_cars},
            traffic_snapshot_writer,
            traffic_snapshot_reader,
            settings_model
        )
