"""Shared reservation-geometry safety rules.

Used by AstarCarController / SafetyController for per-tick acceleration safety,
for lane-change selection, and for the per-tick re-check of a claim that has
already been taken -- `lane_change_blocked` is what tells a claimant that the
space it claimed blind belongs to somebody else and must be given back. Note
that `Car.change_lane` itself checks nothing: a claim is deliberately taken
without looking (see `config.logic_constants`).

Core invariant: a car's reservation [rear, end] always covers its full
worst-case stopping envelope plus BUFFER. A follower is safe iff its projected
reservation end stays behind every leader's worst-case NEXT-tick rear, i.e.
rear + max(0, speed - MAX_DEC). Braking keeps a follower's reservation end
constant while a leader's rear never moves backwards, so any state accepted by
this rule always has a safe successor action (full braking) -- the rule is
inductively collision-free.
"""
from typing import List

from umlsl_sim.config.logic_constants import MAX_ACC, MAX_DEC
from umlsl_sim.simulation.road_network.road_network import LaneSegment, SegmentInfo


def min_next_rear_advance(speed: int) -> int:
    """The least a live car can advance next tick (it may brake fully)."""
    return max(0, speed - MAX_DEC)


def max_end_growth(car) -> int:
    """Upper bound on how far a car's reservation END can advance in one tick
    (it may accelerate fully). end(v) = rear + size + S(v) + BUFFER with
    S the braking sum, so growth = v' + S(v') - S(v) for v' = min(v+MAX_ACC,
    max_speed). size and BUFFER cancel out of the braking-distance difference."""
    if car.get_death_status():
        return 0
    v2 = min(car.speed + MAX_ACC, car.max_speed)
    return v2 + car.get_braking_distance(v2) - car.get_braking_distance(car.speed)


def _other_rear_in_segment(seg, other_id: str, other_reservations: List[SegmentInfo],
                           is_changing_in: bool) -> int | None:
    """Rear offset of another car expressed in `seg` coordinates.

    Negative when the car's rear has not yet entered `seg` (it straddles in
    from earlier segments). For a car mid-lane-change INTO `seg`, offsets map
    1:1 from its parallel source lane, so its source rear is used directly.
    Returns None if the car has no reservation touching `seg` (stale data)."""
    if is_changing_in:
        return abs(other_reservations[0].begin)
    segs = [si.segment for si in other_reservations]
    if seg not in segs:
        return None
    idx = segs.index(seg)
    if idx == 0:
        return abs(other_reservations[0].begin)
    # Rear still on earlier segments: distance until it enters `seg`.
    dist_to_entry = (other_reservations[0].segment.length - abs(other_reservations[0].begin)
                     + sum(other_reservations[j].segment.length for j in range(1, idx)))
    return -dist_to_entry


def rear_end_violation(car, projected: List[SegmentInfo], reservation_management,
                       cars_by_id: dict) -> bool:
    """True if the projected reservation could rear-end any car ahead on any
    lane segment of the projection.

    Everything is measured in path coordinates with origin at the start of
    projected[0].segment. For every car on (or changing into) a projected lane
    segment whose rear is at or ahead of ours, the projected end must stay
    behind that car's worst-case next rear. Cars behind us are ignored -- they
    are responsible for not hitting us. Crossing segments are governed
    separately by the time-to-leave / priority logic."""
    my_rear = abs(projected[0].begin)
    seg_start = 0
    my_end = sum(abs(si.end - si.begin) for si in projected) + my_rear

    for si in projected:
        seg = si.segment
        if isinstance(seg, LaneSegment):
            on_seg = reservation_management.get_cars_on_segment(seg)
            changing_in = reservation_management.get_cars_changing_into_segment(seg)
            for other_id in dict.fromkeys(on_seg + changing_in):
                if other_id == car.id:
                    continue
                other = cars_by_id.get(other_id)
                if other is None:
                    continue
                other_res = reservation_management.get_car_reservations(other_id)
                o_rear = _other_rear_in_segment(seg, other_id, other_res,
                                                other_id not in on_seg)
                if o_rear is None:
                    continue
                o_rear_path = seg_start + o_rear
                if o_rear_path >= my_rear:  # leader (ties treated as leaders)
                    if my_end > o_rear_path + min_next_rear_advance(other.speed):
                        return True
        seg_start += seg.length

    return False


def lane_change_blocked(car, target_seg: LaneSegment, my_begin: int, my_end: int,
                        reservation_management, cars: list) -> bool:
    """True if moving `car`'s reservation [my_begin, my_end] (absolute offsets,
    mapped 1:1 onto `target_seg`) could conflict with any car already on the
    target segment or already moving into it -- claiming it included, since a
    claim is space taken as far as everybody but its holder is concerned.

    Cars ahead: our end must stay behind their worst-case next rear.
    Cars behind: their worst-case next reservation end must stay behind our
    rear, because they cannot see us until our registration lands."""
    on_seg = reservation_management.get_cars_on_segment(target_seg)
    changing_in = reservation_management.get_cars_changing_into_segment(target_seg)
    for other_id in dict.fromkeys(on_seg + changing_in):
        if other_id == car.id:
            continue
        other = next((c for c in cars if c.id == other_id), None)
        if other is None:
            continue
        other_res = reservation_management.get_car_reservations(other_id)
        is_changing_in = other_id not in on_seg
        o_rear = _other_rear_in_segment(target_seg, other_id, other_res, is_changing_in)
        if o_rear is None:
            continue
        if o_rear >= my_begin:  # they are ahead of us (ties: block)
            if my_end > o_rear + min_next_rear_advance(other.speed):
                return True
        else:  # they are behind us
            if is_changing_in:
                o_end = abs(other_res[0].end)
            else:
                segs = [si.segment for si in other_res]
                idx = segs.index(target_seg)
                if idx < len(other_res) - 1:
                    # Their reservation passes through and beyond this segment.
                    return True
                o_end = abs(other_res[idx].end)
            if o_end + max_end_growth(other) > my_begin:
                return True
    return False
