import numpy as np

from typing import Tuple
from umlsl_sim.rl.observations.observation_model import Observation
from umlsl_sim.rl.observations.observation_model_types import ObservationModelType
from umlsl_sim.rl.observations.observation_registry import register_observation_model
from gymnasium import spaces
from umlsl_sim.config.logic_constants import (
    BLOCK_SIZE,
    CLAIM_TIME,
    LANECHANGE_TIME_STEPS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from umlsl_sim.simulation.traffic_environment import TrafficEnv
from umlsl_sim.simulation.road_network.road_network import Direction, LaneSegment, CrossingSegment, SegmentInfo, right_direction

MAX_RES = 16

# Per-car rows have 6 columns. The speed row uses column 0 = is_agent flag,
# column 1 = speed/max_speed, columns 2-5 = 0. Reservation rows are
# [lane_num, direction, x1, y1, x2, y2] as before.
CAR_RES_INFO = 6

# Header: [goal_dx, goal_dy, agent_speed, agent_dir, claim_side, claim_age]
# — agent-relative state. The last two describe the agent's own lane change:
# which way it is going and how far through the manoeuvre it is. Without them
# the withdraw action is unusable, since a policy cannot tell whether it holds
# a claim, nor whether the claim is still withdrawable.
HEADER_INFO = 6

@register_observation_model(ObservationModelType.NUMERIC_OBSERVATION)
class NumbericObservation(Observation):
    """Numeric observation model for RL environment.

    Layout of the flat observation vector:
    - HEADER_INFO values describing the agent's state relative to its current goal
      and its own lane change: [goal_dx, goal_dy, agent_speed, agent_dir,
      claim_side, claim_age]. Deltas are signed and normalized by window size;
      speed by the agent's max_speed; direction by len(Direction). claim_side is
      -1 (claiming right), +1 (claiming left) or 0 (no lane change running), and
      claim_age is the manoeuvre's progress in [0, 1] -- below
      CLAIM_TIME / (CLAIM_TIME + LANECHANGE_TIME_STEPS) the claim can still be
      withdrawn.
    - max_cars * (1 + MAX_RES) * CAR_RES_INFO values for per-car data. The first
      row of each car block is the speed row, with column 0 marking is_agent
      (1.0 for the agent's block, 0.0 for NPCs) and column 1 holding speed.

    `max_cars` is derived from the active scenario (the `game_model` passed at
    construction).
    """

    def __init__(self, game_model: TrafficEnv) -> None:
        super().__init__(game_model)
        self.max_cars = game_model.npcs + (1 if game_model.agent else 0)
        # Used only to normalize lane indices in the per-car reservation rows;
        # the static lane geometry block has been removed from the observation.
        self.max_lanes = max(
            1,
            sum(
                len(road.right_lanes) + len(road.left_lanes)
                for road in game_model.roads
            ),
        )

    def space(self) -> spaces.Space:
        """Define the observation space.

        Returns a Box with values in [-1, 1] (signed to accommodate the goal
        deltas in the header).
        """
        cars_shape = self.max_cars * (1 + MAX_RES) * CAR_RES_INFO
        obs_dim = HEADER_INFO + cars_shape

        return spaces.Box(
            low=-1,
            high=1,
            shape=(obs_dim,),
            dtype=np.float32,
        )

    def observe(self) -> np.ndarray:
        """Build the current observation."""
        header = self._build_header()

        cars = []
        agent_car = self.game_model.agent_car
        for car in self.game_model.cars:
            is_agent = 1.0 if car is agent_car else 0.0
            speed_row = np.array(
                [[is_agent, car.speed / car.max_speed] + [0] * (CAR_RES_INFO - 2)],
                dtype=np.float32,
            )

            reservations = []
            for seg_info in self.reservation_management.get_car_reservations(car.id):

                if isinstance(seg_info.segment, LaneSegment):
                    reservations.append([
                        seg_info.segment.lane.num / self.max_lanes,
                        seg_info.direction.value / len(Direction),
                        *self._get_lane_reservation(seg_info, seg_info.segment),
                    ])

                elif isinstance(seg_info.segment, CrossingSegment):
                    lane_num = seg_info.segment.horiz_lane.num if seg_info.direction in (Direction.RIGHT, Direction.LEFT) else seg_info.segment.vert_lane.num

                    reservations.append([
                        lane_num / self.max_lanes,
                        seg_info.direction.value / len(Direction),
                        *self._get_crossing_reservation(seg_info, seg_info.segment),
                    ])

            while len(reservations) < MAX_RES:
                reservations.append([0] * CAR_RES_INFO)

            reservations = np.array(reservations, dtype=np.float32)
            all_info = np.vstack((speed_row, reservations))
            cars.append(all_info)

        while len(cars) < self.max_cars:
            cars.append(np.zeros((1 + MAX_RES, CAR_RES_INFO), dtype=np.float32))

        cars = np.array(cars, dtype=np.float32).flatten()

        return np.concatenate([header, cars])

    def _build_header(self) -> np.ndarray:
        """Compute the agent-relative header (see the class docstring)."""
        agent = self.game_model.agent_car
        if agent is None:
            return np.zeros(HEADER_INFO, dtype=np.float32)

        goal = agent.goal
        if goal is not None:
            goal_dx = (goal.pos.x - agent.pos.x) / WORLD_WIDTH
            goal_dy = (goal.pos.y - agent.pos.y) / WORLD_HEIGHT
        else:
            goal_dx = 0.0
            goal_dy = 0.0

        speed_norm = agent.speed / agent.max_speed if agent.max_speed else 0.0
        dir_norm = agent.direction.value / len(Direction)
        claim_side, claim_age = self._claim_state(agent)

        return np.array([goal_dx, goal_dy, speed_norm, dir_norm, claim_side, claim_age],
                        dtype=np.float32)

    def _claim_state(self, agent) -> Tuple[float, float]:
        """The agent's outstanding lane change as (side, progress).

        side is -1 for a change to the right, +1 for one to the left, 0 when
        no change is running. progress runs from 0 on the tick the claim was
        registered to 1 on the tick the car lands, so a policy can read off
        both that it holds a claim and whether the claim is still its to give
        back.
        """
        claim = self.reservation_management.get_lane_change_claim(agent.id)
        if claim is None:
            return 0.0, 0.0

        current = self.reservation_management.get_car_reservation(agent.id, 0).segment
        if isinstance(current, LaneSegment):
            num_diff = claim.segment.lane.num - current.lane.num
            side = float(num_diff if right_direction[current.lane.direction] else -num_diff)
            side = max(-1.0, min(1.0, side))
        else:
            side = 0.0

        total = CLAIM_TIME + LANECHANGE_TIME_STEPS
        age = min(1.0, max(0.0, (agent.time - claim.claimed_at) / total))
        return side, age

    def _get_lane_reservation(self, seg_info: SegmentInfo, seg: LaneSegment) -> Tuple[float, float, float, float]:
        """Normalized bbox of a lane-segment reservation, in window coords."""
        if seg_info.direction in (Direction.RIGHT, Direction.LEFT):
            res_begin_x = seg.begin + seg_info.begin
            res_end_x = seg.begin + seg_info.end
            res_begin_y = res_end_y = seg.lane.top
        else:
            res_begin_x = res_end_x = seg.lane.top
            res_begin_y = seg.begin + seg_info.begin
            res_end_y = seg.begin + seg_info.end

        return [
            res_begin_x / WORLD_WIDTH,
            res_begin_y / WORLD_HEIGHT,
            res_end_x / WORLD_WIDTH,
            res_end_y / WORLD_HEIGHT,
        ]

    def _get_crossing_reservation(self, seg_info: SegmentInfo, seg: CrossingSegment) -> Tuple[float, float, float, float]:
        """Normalized bbox of a crossing-segment reservation."""
        lane = seg.horiz_lane if seg_info.direction in (Direction.LEFT, Direction.RIGHT) else seg.vert_lane
        forward = seg_info.direction in (Direction.RIGHT, Direction.UP)
        return self._accumulate_crossing_coords(lane, seg, forward)

    def _accumulate_crossing_coords(self, lane, target_seg, forward: bool) -> Tuple[float, float, float, float]:
        """Walk a lane's segments to locate target_seg and return its bbox."""
        blocks = 0
        segments = lane.segments if forward else reversed(lane.segments)

        for seg in segments:
            blocks += seg.length
            if seg is target_seg:
                if lane.direction is Direction.UP:
                    return [lane.top, blocks - BLOCK_SIZE, lane.top, blocks]
                elif lane.direction is Direction.DOWN:
                    return [lane.top, WORLD_HEIGHT - blocks + BLOCK_SIZE, lane.top, WORLD_HEIGHT - blocks]
                elif lane.direction is Direction.RIGHT:
                    return [blocks - BLOCK_SIZE, lane.top, blocks, lane.top]
                elif lane.direction is Direction.LEFT:
                    return [WORLD_WIDTH - blocks + BLOCK_SIZE, lane.top, WORLD_WIDTH - blocks, lane.top]

        raise ValueError("Target segment not found in lane")
