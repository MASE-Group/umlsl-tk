import math

import heapq
import itertools
from itertools import count

from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.config.logic_constants import (
    ASTAR_CONGESTION_ALPHA,
    BLOCK_SIZE,
    BUFFER,
    CLAIM_TIME,
    CROSSING_MAX_SPEED,
    LANECHANGE_TIME_STEPS,
    LANE_MAX_SPEED,
    MAX_DEC,
)
from umlsl_sim.simulation.road_network.road_network import Goal, Intersection, Segment, LaneSegment, CrossingSegment, SegmentInfo, Point, Problem, direction_sign, true_direction, right_direction, horiz_direction, Color
from umlsl_sim.simulation.reservations.lane_change_claim import LaneChangeClaim
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from typing import Optional, List, Dict


class Car:
    # Monotonic counter used to build deterministic, process-stable car IDs.
    # Tests that rely on exact ID values should call `Car.reset_id_counter()`
    # in setup to make ID assignment reproducible across runs.
    _id_counter: "itertools.count[int]" = itertools.count(1)

    @classmethod
    def reset_id_counter(cls) -> None:
        """Reset the global car-ID counter so subsequent IDs start from 1."""
        cls._id_counter = itertools.count(1)

    def __init__(self,
                 name: str,
                 type: CarType,
                 loc: int,
                 segment: LaneSegment,
                 speed: int,
                 size: int,
                 color: Color,
                 max_speed: int,
                 first_goal: Goal,
                 second_goal: Goal,
                 reservation_management: ReservationManagement) -> None:
        """
        Initialize a Car object.

        Args:
            name (str): The name of the car.
            loc (int): The initial location of the car.
            segment (LaneSegment): The initial lane segment the car is on.
            speed (int): The initial speed of the car.
            size (int): The size of the car.
            color (Color): The color of the car.
            max_speed (int): The maximum speed of the car.
        """
        # fixed variables
        # Use a deterministic counter so IDs are stable across runs given a
        # fixed creation order (which is itself controlled by random.seed).
        self.id = f"{name}_{next(Car._id_counter)}"
        self.name = name
        self.type = type
        self.size = size
        self.color = color
        self.max_speed = max_speed

        # dynamic variables
        self.goal = first_goal
        self.second_goal = second_goal
        self.__dead = False
        self.speed = speed
        self.direction = segment.lane.direction
        self.changing_lane = None
        self.loc = loc
        self.illegal_move = False

        self.time: int = 0
        self.score: int = 0

        # For gui only
        self.pos = Point(0, 0)
        self.w = 0
        self.h = 0

        initial_segment_info = SegmentInfo(segment=segment,
                                           begin=self.loc,
                                           end=direction_sign[self.direction] * (abs(self.loc) + self.get_braking_distance()),
                                           direction=self.direction)
        reservation_management.add_car_reservation(car_id=self.id, segment_info=initial_segment_info)

        self.update_position(reservation_management)

    def move(self, rm: ReservationManagement) -> bool:
        if self.__dead:
            return False

        reservations = rm.get_car_reservations_view(self.id)

        self.loc += direction_sign[reservations[0].direction] * self.speed
        self.check_reservation(rm)
        self.time += 1

        self._extend_reservations(rm)
        # `reservations` is the live list — appended items are visible.

        self._update_crossing_claim(rm)

        while abs(self.loc) > reservations[0].segment.length:
            passed = rm.pop_car_reservation(self.id, 0)
            self.loc = direction_sign[reservations[0].direction] * (abs(self.loc) - passed.segment.length)

        reservations[0].begin = self.loc
        reservations[0].turn = False
        self.direction = reservations[0].direction

        # Single pass: time-to-leave for crossings, then expand non-tail ends, then set tail.
        crossing_speed = max(1, min(self.speed, CROSSING_MAX_SPEED))
        cumulative = 0
        n = len(reservations)
        for i, seg_info in enumerate(reservations):
            cumulative += abs(seg_info.end - seg_info.begin)
            if isinstance(seg_info.segment, CrossingSegment):
                seg_info.segment.crossing_segment_state.add_time_to_leave(
                    self.id, self.time + math.ceil(cumulative / crossing_speed))

        consumed = 0
        for i in range(n - 1):
            s = reservations[i]
            s.end = direction_sign[s.direction] * s.segment.length
            consumed += abs(s.end - s.begin)

        tail = reservations[-1]
        end_off = max(self.size + BUFFER, self.get_braking_distance() - consumed)
        tail.end = direction_sign[tail.direction] * (end_off + abs(tail.begin))

        self.update_position(rm)
        return True

    def _update_crossing_claim(self, rm: ReservationManagement) -> None:
        """Register or renew this car's claim on the intersection ahead of it.

        The claim is registered once the reservation reaches within BLOCK_SIZE
        of the end of the last reserved lane segment, and renewed on every tick
        after that. IntersectionState holds it as a lease: renewals that report
        no progress eventually reorder the claim behind the other contenders
        and then withdraw it, so a car that cannot move stops holding the
        intersection closed against everybody else. A withdrawn claim is simply
        registered again by the next tick on which the car is still approaching,
        which puts it at the back of the queue.
        """
        tail = rm.get_car_reservation(self.id, -1)
        segment = tail.segment
        if not isinstance(segment, LaneSegment) or segment.end_crossing is None:
            return

        state = segment.end_crossing.intersection.intersection_state
        if state.get_car_priority(self.id) is None:
            if segment.length - abs(tail.end) <= BLOCK_SIZE:
                state.add_car_priority(self.id, self.time)
        else:
            state.renew_car_priority(self.id, self.time, made_progress=self.speed > 0)

    def _extend_reservations(self, rm: ReservationManagement) -> None:
        reservations = rm.get_car_reservations_view(self.id)
        braking = self.get_braking_distance()
        total_seg_length = sum(r.segment.length for r in reservations)

        if abs(self.loc) + braking < total_seg_length:
            return

        next_segs = self.get_next_segment(rm)  # FIX: was missing
        if not next_segs or len(next_segs) < 2:
            return
        next_segs = next_segs[1:]                        # drop current tail

        next_segs[0].intersection.intersection_state.pop_car_priority(self.id)

        crossing_speed = max(1, min(self.speed, CROSSING_MAX_SPEED))
        last_dir = reservations[-1].direction
        cumulative = sum(abs(r.end - r.begin) for r in reservations)

        for i, segment in enumerate(next_segs):
            if isinstance(segment, LaneSegment):
                seg_dir = segment.lane.direction
                jump = abs(self.loc) + braking - total_seg_length
                end_off = max(jump, self.size + BUFFER)
            else:  # CrossingSegment
                seg_dir = next(d for d, s in segment.connected_segments.items()
                            if s is next_segs[i + 1])
                end_off = segment.length

            sign = direction_sign[seg_dir]
            seg_info = SegmentInfo(segment, 0, sign * end_off, seg_dir, seg_dir != last_dir)
            rm.add_car_reservation(self.id, seg_info)

            cumulative += end_off
            total_seg_length += segment.length

            if isinstance(segment, CrossingSegment):
                segment.crossing_segment_state.add_time_to_leave(
                    self.id, self.time + math.ceil(cumulative / crossing_speed))

            last_dir = seg_dir

    def change_speed(self, speed_diff: int) -> None:
        """
        Change the speed of the car.

        Args:
            speed_diff (int): The difference in speed to apply.

        Returns:
            None.
        """
        self.speed = max(min(self.speed + speed_diff, self.max_speed), 0)

    def get_adjacent_lane_segments(self, reservation_management: ReservationManagement, lane_segment: None | LaneSegment = None) -> None | List[LaneSegment]:
        """
        Get the adjacent lane segment.

        Args:
            lane_diff (int): The difference in lane number.
            lane_segment (LaneSegment, optional): The current lane segment. Defaults to using the first lane segment in the reservation.

        Returns:
            LaneSegment: The adjacent lane segment.
        """
        reservations = reservation_management.get_car_reservations(self.id)
        if lane_segment is None:
            if isinstance(reservations[0].segment, LaneSegment):
                lane_segment = reservations[0].segment
            else:
                return None

        lanes = lane_segment.lane.road.right_lanes if right_direction[lane_segment.lane.direction] \
            else lane_segment.lane.road.left_lanes
        current_seg_num = lane_segment.num
        return [lane.segments[current_seg_num] for lane in lanes]
    
    def get_adjacent_lane_segment(self, reservation_management: ReservationManagement, lane_diff: int, lane_segment: None | LaneSegment = None) -> None | LaneSegment:
        """
        Get the adjacent lane segment.

        Args:
            lane_diff (int): The difference in lane number.
            lane_segment (LaneSegment, optional): The current lane segment. Defaults to using the first lane segment in the reservation.

        Returns:
            LaneSegment: The adjacent lane segment.
        """
        reservations = reservation_management.get_car_reservations(self.id)
        if lane_segment is None:
            if isinstance(reservations[0].segment, LaneSegment):
                lane_segment = reservations[0].segment
            else:
                return None

        lanes = lane_segment.lane.road.right_lanes if right_direction[lane_segment.lane.direction] \
            else lane_segment.lane.road.left_lanes
        
        actual_lane_diff = (1 if right_direction[lane_segment.lane.direction] else -1) * lane_diff
        lane_num = lane_segment.lane.num + actual_lane_diff
        current_seg_num = lane_segment.num

        if 0 <= lane_num < len(lanes):
            return  lanes[lane_num].segments[current_seg_num]
        return None

    def change_lane(self, reservations_management: ReservationManagement,
                    lane_diff: int) -> bool | Problem:
        """
        Claim the adjacent lane segment, opening a lane change.

        No collision check is made here: a claim is deliberately taken blind.
        For the next CLAIM_TIME ticks the car drives on in its own lane while
        its controller watches the claim, and `withdraw_claim` gives the lane
        back the moment the claim turns out to overlap somebody. Only what the
        car cannot discover later is refused up front -- that there is a lane
        to move into, and that the car is on a plain lane segment rather than
        astride a crossing.

        Args:
            lane_diff (int): The difference in lane number.

        Returns:
            bool: True if the claim was registered, False if there was nothing
                to claim (no lane change asked for, or one already running).
            Problem: If the car is in no position to change lane at all.
        """
        reservations = reservations_management.get_car_reservations(self.id)

        # case 1: car is not in a lane segment -> return problem
        if not (isinstance(reservations[0].segment, LaneSegment) and \
                len(reservations) == 1):
            return Problem.CHANGE_LANE_WHILE_CROSSING

        if lane_diff == 0:
            return False

        # case 2: a claim or a committed change is already running -> a second
        # one would have nowhere to put the car; keep the first.
        if reservations_management.get_lane_change_claim(self.id) is not None:
            return False

        adjacent_lane_seg = self.get_adjacent_lane_segment(reservations_management, lane_diff)

        # case 3: there is no adjacent lane segment -> return problem
        if adjacent_lane_seg is None:
            return Problem.NO_ADJACENT_LANE

        self.changing_lane = True
        reservations_management.set_lane_change_claim(
            self.id, LaneChangeClaim(segment=adjacent_lane_seg, claimed_at=self.time))
        return True

    def withdraw_claim(self, reservations_management: ReservationManagement) -> bool:
        """
        Give up a claim taken on an earlier tick and stay in the current lane.

        Available only while the claim is uncommitted, which is the first
        CLAIM_TIME ticks of the manoeuvre. Once the claim has become a
        reservation the car is half-way into the target lane and there is
        nothing left to give back.

        Returns:
            bool: True if a claim was withdrawn, False if there was no
                withdrawable claim to withdraw.
        """
        claim = reservations_management.get_lane_change_claim(self.id)
        if claim is None or claim.committed:
            return False

        reservations_management.remove_lane_change_claim(self.id)
        self.changing_lane = False
        return True

    def check_reservation(self, reservations_management: ReservationManagement) -> bool:
        """
        Advance an outstanding lane change by one tick.

        Two deadlines, both counted from the tick the claim was registered:

        * at CLAIM_TIME the claim becomes a reservation. Nobody is consulted --
          the controller had CLAIM_TIME ticks to withdraw and did not, so the
          car takes the lane.
        * at CLAIM_TIME + LANECHANGE_TIME_STEPS the car lands: its reservation
          moves over to the target segment and the claim is cleared.

        Returns:
            bool: True on the tick the car lands on the target lane, False on
            every other tick.
        """
        if not self.changing_lane:
            return False

        claim = reservations_management.get_lane_change_claim(self.id)
        if claim is None:
            return False

        elapsed = self.time - claim.claimed_at

        if not claim.committed:
            if elapsed >= CLAIM_TIME:
                reservations_management.commit_lane_change_claim(self.id)
            # Claiming or just committed: the car is still wholly in its own
            # lane, and its reservation stays where it is.
            return False

        if elapsed < CLAIM_TIME + LANECHANGE_TIME_STEPS:
            # Mid-change but not yet due: the reservation stays where it is.
            return False

        self.changing_lane = False

        reservations = reservations_management.get_car_reservations(self.id)
        new_reserve = SegmentInfo(claim.segment,
                                  reservations[0].begin,
                                  reservations[0].end,
                                  reservations[0].direction)
        for _ in reservations:
            reservations_management.pop_car_reservation(self.id, 0)

        reservations_management.add_car_reservation(self.id, new_reserve)
        reservations_management.remove_lane_change_claim(self.id)

        self.update_position(reservations_management)

        return True

    def get_braking_distance(self, speed: int = None) -> int:
        """
        Get the braking distance of the car.

        Args:
            speed (int, optional): The speed of the car. Defaults to None.

        Returns:
            int: The braking distance of the car.
        """
        if self.get_death_status():
            return self.speed

        if speed is None:
            speed = self.speed
        if speed < 0:
            raise ValueError(
                f"get_braking_distance requires non-negative speed; got {speed} "
                f"for car {self.id!r} (type={self.type})."
            )
        # braking = math.ceil(speed**2  // (2 * MAX_DEC))

        braking = 0
        while speed > 0:
            braking += speed
            speed -= MAX_DEC
        # BLOCK_SIZE // 2 additional distance when speed = 0
        return self.size + braking + BUFFER
    
    def get_size_segments(self, reservations_management: ReservationManagement) -> List[SegmentInfo]:
        """
        Get the segments occupied by the car.

        Returns:
            list[dict]: The list of segments occupied by the car.
        """
        reservations = reservations_management.get_car_reservations(self.id)
        segments: list[SegmentInfo] = []
        accumulated_size = 0
        i = 0
        while accumulated_size < self.size:
            seg_info = reservations[i]
            begin = abs(seg_info.begin)
            end = abs(seg_info.end)
            diff = end - begin   
            remaining = min(diff, self.size - accumulated_size)
            segments.append(SegmentInfo(seg_info.segment, 
                                        seg_info.begin, 
                                        seg_info.begin + (1 if true_direction[seg_info.direction] else -1) * remaining, 
                                        seg_info.direction))
            accumulated_size += diff
            i += 1
        return segments


    def get_death_status(self) -> bool:
        return self.__dead
    
    def get_next_segment(self, reservation_management: ReservationManagement,
                         last_seg: Segment | None = None) -> List[Segment]:
        """
        Get the next segment for the car to move to.

        Args:
            last_seg (Segment): The last segment the car was on.
            cars (List[Car], optional): Other cars in the simulation; used by
                astar's congestion-aware cost. If omitted, astar falls back to
                a length-only plan (no live-traffic info).
        Returns:
             List[Segment]: The planned segments up to and including the next
                LaneSegment, starting with `last_seg` itself. Empty when no
                such plan exists -- A* found no route, or the route it found
                stops on `last_seg`. Callers treat "no plan" and "a plan too
                short to extend into" alike, so both are the empty list rather
                than one being None and the other [].
        """
        reservations = reservation_management.get_car_reservations(self.id)

        if last_seg is None:
            last_seg = reservations[-1].segment

        if reservations[0].segment == self.goal.lane_segment:
            #case 1: cur seg == goal seg -> preplan path to second goal
            segs = self.astar(reservations_management=reservation_management,
                              start_seg=last_seg, goal=self.second_goal)

        else:
            #case 2: cur seg != goal seg -> plan path to first goal(e.g. for alternative lanes (right, left)
            segs = self.astar(reservations_management=reservation_management,
                              start_seg=last_seg)
        


        if len(segs) < 2:
            # Either A* found nothing at all, or the only segment it found is
            # the one we are already on -- neither is something to extend into.
            return []

        for i in range(1, len(segs)):
            if isinstance(segs[i], LaneSegment):
                return segs[0:i + 1]

        return []

    def update_position(self, reservation_management: ReservationManagement) -> None:
        """
        Update the position of the car, based on the current lane segment, location, direction and speed.

        Returns:
            tuple[int, int, int, int]: The updated position (x, y, w, h) of the car.
        """
        """ Returns the bottom left corner of the car """
        segment_info = reservation_management.get_car_reservation(self.id, 0)
        segment = segment_info.segment
        is_lane_seg = isinstance(segment, LaneSegment)

        if is_lane_seg:
            seg_begin = segment.begin
        if horiz_direction[self.direction]:
            if not is_lane_seg:
                seg_begin = segment.vert_lane.top if true_direction[segment_info.direction] else segment.vert_lane.top + BLOCK_SIZE
            self.pos.y = segment.lane.top \
                if is_lane_seg else segment.horiz_lane.top
            self.pos.x = seg_begin + self.loc - (0 if true_direction[segment_info.direction] else self.size)
            self.w = self.size
            self.h = BLOCK_SIZE
        else:
            if not is_lane_seg:
                seg_begin = segment.horiz_lane.top if true_direction[segment_info.direction] else segment.horiz_lane.top + BLOCK_SIZE
            self.pos.x = segment.lane.top \
                if is_lane_seg else segment.vert_lane.top
            self.pos.y = seg_begin + self.loc - (0 if true_direction[segment_info.direction] else self.size)
            self.w = BLOCK_SIZE
            self.h = self.size

    def get_position(self) -> tuple[int, int, int, int]:
        """
        returns the position of the car.

        Returns:
            tuple[int, int, int, int]: The updated position (bottom left corner) (x, y, w, h) of the car.
        """

        return self.pos.x, self.pos.y, self.w, self.h
    
    def get_center(self, reservation_management: ReservationManagement) -> List:
        """
        Get the center point of the car.

        Returns:
            Point: The center point of the car.
        """
        reservation = reservation_management.get_car_reservation(self.id, 0)
        if horiz_direction[reservation.direction]:
            return [self.pos.x + self.size // 2, self.pos.y + BLOCK_SIZE // 2]
        else:
            return [self.pos.x + BLOCK_SIZE // 2, self.pos.y + self.size // 2]

    def astar(self, reservations_management: ReservationManagement,
            start_seg: Segment = None, goal: Goal = None) -> List[Segment]:

        start_seg = (reservations_management.get_car_reservation(self.id, -1).segment
                    if start_seg is None else start_seg)
        goal_seg  = self.goal.lane_segment if goal is None else goal.lane_segment

        if start_seg is goal_seg:
            return [start_seg]

        def heuristic(seg: Segment) -> float:
            # Center of seg in (x, y)
            match seg:
                case LaneSegment():
                    cx = seg.end if seg.lane.road.horizontal else seg.lane.top
                    cy = seg.lane.top if seg.lane.road.horizontal else seg.end
                case CrossingSegment():
                    cx = seg.vert_lane.top  + BLOCK_SIZE // 2   # x
                    cy = seg.horiz_lane.top + BLOCK_SIZE // 2   # y
                case _:
                    return 0.0
            gx = goal_seg.begin if goal_seg.lane.road.horizontal else goal_seg.lane.top
            gy = goal_seg.lane.top if goal_seg.lane.road.horizontal else goal_seg.begin
            return math.dist((cx, cy), (gx, gy))

        tiebreak   = count()
        open_heap  = [(heuristic(start_seg), next(tiebreak), start_seg)]
        came_from: dict[Segment, Segment] = {}
        g_score    = {start_seg: 0}
        closed: set[Segment] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)

            if current in closed:
                continue
            closed.add(current)

            if current is goal_seg:
                path: list[Segment] = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_seg)
                path.reverse()
                return path

            match current:
                case LaneSegment():
                    neighbors = [current.end_crossing] if current.end_crossing else []
                case CrossingSegment():
                    neighbors = [s for s in current.connected_segments.values() if s is not None]
                case _:
                    neighbors = []

            for nb in neighbors:
                if nb in closed:
                    continue
                tg = g_score[current] + current.length
                if tg < g_score.get(nb, float('inf')):
                    came_from[nb] = current
                    g_score[nb]   = tg
                    heapq.heappush(open_heap, (tg + heuristic(nb), next(tiebreak), nb))

        return []   # no path found — caller must handle empty list

    def astar_speed(self, reservations_management: ReservationManagement,
            cars: Optional[List["Car"]] = None,
            start_seg: Segment = None, goal: Goal = None,
            ignore_blocked: bool = False) -> List[Segment]:
        """Time-weighted A* with intersection-congestion penalty.

        Edge cost into a neighbor segment: ``segment.length / effective_speed``,
        where ``effective_speed`` is the min speed of other cars on that segment
        (falling back to ``segment.max_speed`` when empty). Crossing segments
        get an additional soft penalty proportional to the number of cars on
        the four crossing cells of their intersection plus the cars queued on
        the four approach lane segments.

        A neighbor is treated as impassable when any other car on it has speed
        0. If no path is found under that rule we retry with
        ``ignore_blocked=True`` so the caller never gets stuck without a plan.
        """

        start_seg = (reservations_management.get_car_reservation(self.id, -1).segment
                    if start_seg is None else start_seg)
        goal_seg  = self.goal.lane_segment if goal is None else goal.lane_segment

        if start_seg is goal_seg:
            return [start_seg]

        car_by_id = {c.id: c for c in cars} if cars else {}

        def seg_min_other_speed(seg: Segment) -> Optional[int]:
            """Min speed of OTHER cars on `seg`. None if empty / unknown."""
            speeds: list[int] = []
            for cid in reservations_management.get_cars_on_segment(seg):
                if cid == self.id:
                    continue
                other = car_by_id.get(cid)
                if other is not None:
                    speeds.append(other.speed)
            return min(speeds) if speeds else None

        def is_blocked(seg: Segment) -> bool:
            spd = seg_min_other_speed(seg)
            return spd is not None and spd == 0

        def edge_cost(seg: Segment) -> float:
            spd = seg_min_other_speed(seg)
            effective = seg.max_speed if spd is None else max(spd, 1)
            cost = seg.length / effective
            if isinstance(seg, CrossingSegment):
                intersection: Intersection = seg.intersection
                congestion = 0
                for cseg in intersection.segments:
                    congestion += sum(
                        1 for cid in reservations_management.get_cars_on_segment(cseg)
                        if cid != self.id
                    )
                    for conn in cseg.connected_segments.values():
                        if isinstance(conn, LaneSegment) and conn.end_crossing is cseg:
                            congestion += sum(
                                1 for cid in reservations_management.get_cars_on_segment(conn)
                                if cid != self.id
                            )
                cost *= 1.0 + ASTAR_CONGESTION_ALPHA * congestion
            return cost

        def heuristic(seg: Segment) -> float:
            # Lower-bound time-to-goal: straight-line distance / best lane speed.
            match seg:
                case LaneSegment():
                    cx = seg.end if seg.lane.road.horizontal else seg.lane.top
                    cy = seg.lane.top if seg.lane.road.horizontal else seg.end
                case CrossingSegment():
                    cx = seg.vert_lane.top  + BLOCK_SIZE // 2   # x
                    cy = seg.horiz_lane.top + BLOCK_SIZE // 2   # y
                case _:
                    return 0.0
            gx = goal_seg.begin if goal_seg.lane.road.horizontal else goal_seg.lane.top
            gy = goal_seg.lane.top if goal_seg.lane.road.horizontal else goal_seg.begin
            return math.dist((cx, cy), (gx, gy)) / LANE_MAX_SPEED

        tiebreak   = count()
        open_heap  = [(heuristic(start_seg), next(tiebreak), start_seg)]
        came_from: dict[Segment, Segment] = {}
        g_score: dict[Segment, float] = {start_seg: 0.0}
        closed: set[Segment] = set()

        while open_heap:
            _, _, current = heapq.heappop(open_heap)

            if current in closed:
                continue
            closed.add(current)

            if current is goal_seg:
                path: list[Segment] = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_seg)
                path.reverse()
                return path

            match current:
                case LaneSegment():
                    neighbors = [current.end_crossing] if current.end_crossing else []
                case CrossingSegment():
                    neighbors = [s for s in current.connected_segments.values() if s is not None]
                case _:
                    neighbors = []

            for nb in neighbors:
                if nb in closed:
                    continue
                if not ignore_blocked and nb is not goal_seg and is_blocked(nb):
                    continue
                tg = g_score[current] + edge_cost(nb)
                if tg < g_score.get(nb, float('inf')):
                    came_from[nb] = current
                    g_score[nb]   = tg
                    heapq.heappush(open_heap, (tg + heuristic(nb), next(tiebreak), nb))

        if not ignore_blocked:
            # Fallback: a stopped car blocks every viable route. Replan ignoring
            # the impassable filter so the caller still has a plan to follow.
            return self.astar_speed(reservations_management, cars, start_seg, goal,
                              ignore_blocked=True)
        return []   # no path found — caller must handle empty list

    def handle_car_death(self, reservation_management: ReservationManagement) -> None:
        index = len(self.get_size_segments(reservation_management))
        # A dead car never moves again, so it can never renew or release a claim
        # of its own. Withdraw every claim it holds -- including the one on the
        # intersection ahead of a lane segment it was still queued on, which
        # would otherwise block that intersection for the rest of the run.
        for seg_info in reservation_management.get_car_reservations(self.id):
            segment = seg_info.segment
            if isinstance(segment, CrossingSegment):
                segment.intersection.intersection_state.pop_car_priority(self.id)
            elif isinstance(segment, LaneSegment) and segment.end_crossing is not None:
                segment.end_crossing.intersection.intersection_state.pop_car_priority(self.id)

        while index < len(reservation_management.get_car_reservations(self.id)):
            reservation_management.pop_car_reservation(self.id, index)

        for seg_info in reservation_management.get_car_reservations(self.id):
            if isinstance(seg_info.segment, CrossingSegment):
                seg_info.segment.crossing_segment_state.add_time_to_leave(self.id, float('inf'))

        # The wreck will never complete the manoeuvre, so the lane it was
        # moving into must not stay taken on its behalf.
        reservation_management.remove_lane_change_claim(self.id)
        self.changing_lane = False

        self.speed = 0
        self.__dead = True