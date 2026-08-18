# Findings from building the `factories` / `simulation` / `control` test suite

Everything below came out of writing [`tests/`](.) against
[`src/umlsl_sim/factories/`](../src/umlsl_sim/factories/),
[`src/umlsl_sim/simulation/`](../src/umlsl_sim/simulation/) and
[`src/umlsl_sim/control/`](../src/umlsl_sim/control/).

Entries 1–10 were **fixed**, and the tests assert the intended behaviour.
Entries 11–17 are **flagged only** — they are unused code, latent risks, or
questions of intent that are yours to settle.

Every entry names the test that covers it, so each finding has something that
fails if the behaviour drifts back.

---

## Fixed: unnecessary side effects

### 1. `create_segments` reordered the caller's list and could not be run twice

**Where:** [`factories/create_segments.py`](../src/umlsl_sim/factories/create_segments.py)
**Covered by:** `tests/test_factories_create_segments.py::TestCreateSegmentsSideEffects`

Two separate problems in one function:

* `roads.sort(key=lambda r: r.top)` sorted **the caller's list in place**. The
  algorithm does need a top-down order, but the caller never asked for their
  list to be rearranged. `TrafficEnv.__init__` keeps that same list as
  `self.roads`, so building an environment silently permuted the road order the
  scenario file specified — which in turn changed which segment each randomly
  placed car landed on for a given seed.
* Segments are *appended* to `lane.segments`, so a second call on the same roads
  produced a doubled graph: each lane ended up with two interleaved copies of
  its segments, and the wrap-around successor wiring (`% len(lane.segments)`)
  then connected the wrong ones. Nothing in the package calls it twice today,
  but `gui/manual_drive_window.py:42` calls it on roads it did not build, so it
  is one refactor away from mattering.

**Fix:** sort a local copy, and clear each lane's segment list before building
so a rebuild replaces the graph rather than compounding it.

> Note: seeded runs place cars differently than before this change, because the
> road order the RNG draws against is no longer permuted. No behaviour is worse
> — the sequence is simply the one the scenario file actually describes.

### 2. `SegmentOccupancyTracker.get_cars_on_segment` wrote to the table on every read

**Where:** [`simulation/reservations/segment_occupancy_tracker.py`](../src/umlsl_sim/simulation/reservations/segment_occupancy_tracker.py)
**Covered by:** `tests/test_reservations.py::TestSegmentOccupancyTracker::test_reading_an_unoccupied_segment_does_not_record_it`

A miss inserted an empty list before returning it. The safety checks
(`rear_end_violation`, `_violates_safety`, `astar_speed`) query *every* segment
of a projected route, most of them empty, so the occupancy table grew into a
record of every segment ever considered rather than every segment occupied.

**Fix:** `return list(self.__segment_occupancy_dict.get(segment, ()))`.

### 3. `get_reserved_lane_change_segment` raised `KeyError` for a car that never changed lane

**Where:** [`simulation/reservations/reservation_management.py`](../src/umlsl_sim/simulation/reservations/reservation_management.py)
**Covered by:** `tests/test_reservations.py::TestReservationManagementLaneChanges::test_a_car_that_never_registered_one_reads_as_none`

The dict was only ever populated by `set_reserved_lane_change_segment`, so a
plain `[car_id]` lookup raised for any car that had not yet changed lane. Every
caller (`Car.check_reservation`, both controllers' `_lane_change_will_complete`)
already treats `None` as "nothing pending", and the return type was already
annotated `| None`.

**Fix:** `.get(car_id)`.

---

## Fixed: behavioural bugs

### 4. `collision_check` reported two exactly coincident cars as *not* colliding

**Where:** [`simulation/event_checks.py`](../src/umlsl_sim/simulation/event_checks.py)
**Covered by:** `tests/test_simulation_event_checks.py::TestCollisionCheck::test_two_exactly_coincident_bodies_collide`

The test was four strict three-way comparisons:

```python
if begin2 < begin1 < end2: ... elif begin2 < end1 < end2: ...
elif begin1 < begin2 < end1: ... elif begin1 < end2 < end1: ...
```

Every one of those is false when the two intervals are **identical** — so total
overlap, the worst collision there is, was the single case the check missed.

**Fix:** ordinary interval overlap, `lo1 < hi2 and lo2 < hi1`, with the endpoints
ordered via `sorted()` so reverse lanes need no special case. Bumper-to-bumper
(`hi1 == lo2`) is still not a collision, as before.

One consequence worth knowing: `collision_check(car, car)` is now `True`, since a
car totally overlaps itself. `TrafficEnv._execute_action` already excludes the
car from its own crash scan, and a test pins that requirement.

### 5. `Car.check_reservation` fell off the end returning `None`

**Where:** [`simulation/car.py`](../src/umlsl_sim/simulation/car.py)
**Covered by:** `tests/test_simulation_car.py::TestCheckReservation`

Declared `-> bool`, but the "mid-change, not yet due" path reached the end of
the function and returned `None`. Harmless today (the only caller, `Car.move`,
discards the result) but it makes the return value unusable to anyone else.

**Fix:** explicit `return False`.

### 6. `Car.get_next_segment` returned `None` where its signature promised a list

**Where:** [`simulation/car.py`](../src/umlsl_sim/simulation/car.py)
**Covered by:** `tests/test_simulation_car.py::TestGetNextSegment::test_no_plan_is_the_empty_list_rather_than_none`

Declared `-> List[Segment]`, it returned `None` on two paths (A* found nothing;
A* found only the current segment) and `[]` on a third — three spellings of the
same "no plan". Both call sites already write `if not next_segs or len(...) < 2`,
so the distinction was never used, only available to be got wrong.

**Fix:** one `if len(segs) < 2: return []`.

### 7. `GameHistory` keyed each car's action list by its display *name*

**Where:** [`simulation/episode_history.py`](../src/umlsl_sim/simulation/episode_history.py)
**Covered by:** `tests/test_simulation_episode_history.py::TestGameHistoryRecording::test_two_cars_with_the_same_name_keep_separate_records`

`_car_entry_key` was `car_type.name + ":" + car_name`. `_pick_name_color` keeps
*randomly* placed cars uniquely named, but a scenario may name two predefined
cars alike (`CarSpec.name` is taken verbatim), and two cars sharing a name meant:

* `_create_new_car_entry` overwrote the first car's entry with an empty list;
* both cars then appended into one list, so the recording interleaved two cars'
  actions under one key and `action_length` double-counted;
* a replay would have re-driven that merged list on both cars.

Additionally `add_taken_action` did `self.action_history_dict.get(key).append(...)`
— an `AttributeError` on `None` for any unregistered car.

**Fix:** key on `car.id`, which carries a monotonic counter and is unique by
construction; raise a `KeyError` naming `set_list_of_cars` when a car was never
registered.

### 8. `GameHistory.replay` raised before drawing anything

**Where:** [`simulation/episode_history.py`](../src/umlsl_sim/simulation/episode_history.py)
**Covered by:** `tests/test_simulation_episode_history.py::TestReplay`, `tests/integration/test_control_integration.py::TestRecordAndReplay`

The loop was stale against the current `Car` API — it called `car.reset()` (no
such method) and `car.move()` / `car.change_lane(lane_change)` without the
`ReservationManagement` both now require. The docstring flagged it as broken and
named the open question: *does a replay re-run reservations, or only re-position
cars?*

**Fix — and the answer to that question:** a recording holds **actions**, so a
replay re-drives them through the live `Car` API. That needs the state the
episode started from, which a `Car` cannot supply on its own (a car does not
hold its segment; the reservation book does). So:

* `set_list_of_cars` now takes an optional `ReservationManagement` and captures
  a frozen `CarSnapshot` per car — the constructor arguments, including the
  anchor segment. `TrafficEnv.reset()` calls it at exactly the moment the cars
  are in their initial state.
* `replay` rebuilds real `Car` objects from those snapshots on a
  `ReservationManagement` **of its own**, so a replay neither reads nor disturbs
  a live simulation and replays identically every time.
* It draws **one frame per tick**, after every car has acted. The old loop drew
  one frame per *car* per tick.
* Without snapshots it raises `HistoryNotReplayable` with an explanation, rather
  than an `AttributeError` from three layers down.

See finding **16** for the part of this that is still open.

### 9. `TrafficEnv.time` counted car-actions, not ticks

**Where:** [`simulation/traffic_environment.py`](../src/umlsl_sim/simulation/traffic_environment.py)
**Covered by:** `tests/test_traffic_environment.py::TestPlayStep::test_the_environment_clock_advances_once_per_step`, `::test_the_environment_clock_keeps_step_with_the_cars`

`self.time += 1` sat inside `_execute_action`, which runs once per living car. A
world with eight cars advanced its clock eight times per `play_step`, while every
`Car.time` advanced by one — so the environment clock ran `len(cars)` times
faster than the cars it was meant to be timing, and diverged further as cars
died. The crossing time-to-leave arithmetic is written against `Car.time`, so
the two were not measuring the same thing at all.

Nothing in the package reads `TrafficEnv.time`, which is why the discrepancy was
invisible.

**Fix:** one increment per `play_step`. An integration test now asserts
`car.time == env.time` for every car after a run.

### 10. `_choose_lane_change` built a `SegmentInfo` it then discarded

**Where:** [`control/astar/astar_car_controller.py`](../src/umlsl_sim/control/astar/astar_car_controller.py)
**Covered by:** existing lane-change tests in `tests/test_control_astar.py`

Cosmetic: the candidate `SegmentInfo` was constructed before the
`lane_change_blocked` guard that may `continue` past it. Moved after the guard.

---

## Flagged only

### 11. `Car.astar_speed` is never called, and its tuning constant is inert

**Where:** [`simulation/car.py`](../src/umlsl_sim/simulation/car.py)
**Covered by:** `tests/test_simulation_car.py::TestAstarSpeed` (behaviour pinned, not endorsed)

`astar_speed` is the congestion-aware planner: time-weighted edges, a penalty
for busy intersections, an impassability rule for stopped cars, and an
`ignore_blocked` retry so a caller always gets a plan. The only reference to it
anywhere in the package is its own recursive fallback — `Car.get_next_segment`
calls the plain, length-only `astar`.

Consequently `ASTAR_CONGESTION_ALPHA` is dead too, despite
[`logic_constants.py`](../src/umlsl_sim/config/logic_constants.py) documenting it
as live and explaining where it belongs. That comment also refers to
`Car.find_path`, which does not exist.

**Decision for you:** switch `get_next_segment` over to `astar_speed`, or delete
it and the constant. I have not guessed which — routing every NPC through a
congestion-aware planner is a change to the traffic model, not a cleanup. The
tests cover it either way.

### 12. Dead code inventory

None of the following is referenced anywhere in `src/`, `benchmarks/` or
`manual_tests/`. Where a test exists it pins current behaviour so that removing
the code is a deliberate act rather than an accident.

| Symbol | Where | Note |
|---|---|---|
| `Road.get_outer_lane_segment` | `road_network.py` | Typed `Segment`, but reads `.num`, which only `LaneSegment` has — passing a `CrossingSegment` is an `AttributeError`. Pinned in `TestRoadGetOuterLaneSegment`. |
| `CrossingSegment.get_road` | `road_network.py` | Pinned in `TestCrossingSegmentGetRoad`. |
| `IntersectionState.get_priority_items` | `intersection_state.py` | Used only by the tests now; genuinely useful for diagnostics. |
| `ReservationManagement.update_car_reservation_begin` / `_end` / `_turn` | `reservation_management.py` | `Car.move` mutates `SegmentInfo` fields directly through the live view instead. Two ways to do one thing. |
| `Car.get_position` | `car.py` | The GUI reads `car.pos` / `car.w` / `car.h` directly. |
| `TrafficEnv.moved` | `traffic_environment.py` | Set in `__init__` and `reset`, never read, and documented as an attribute in the class docstring. Pinned in `TestMovedFlag`. |
| `Problem.NO_NEXT_SEGMENT`, `SLOWER_WHILE_0`, `FASTER_WHILE_MAX`, `LANE_TOO_SHORT` | `road_network.py` | `Car.change_lane` is the only producer of `Problem` and returns only the other two members. Pinned in `TestPointAndProblem`. |
| `CLAIMTIME`, `JUMP_TIME_STEPS` | `logic_constants.py` | Documented as live. |
| `clock_wise`, `direction_axis` | `road_network.py` | Pinned in `TestDirectionTables` (they are at least self-consistent). |

### 13. `_pick_name_color` fails silently when the palettes run out

**Where:** [`factories/create_cars.py`](../src/umlsl_sim/factories/create_cars.py)
**Covered by:** `tests/test_factories_create_cars.py::TestPickNameColor::test_an_exhausted_palette_yields_a_nameless_black_car`

With every name taken it returns `("", (0, 0, 0))` — an unnamed black car rather
than an error, and one that would then collide with any *other* exhausted car in
anything keyed by name. Unreachable in practice: the two palettes hold 573 names
between them and `TrafficEnv`'s segment-capacity check refuses far fewer cars
than that. Worth a `raise` if you want the failure mode to be loud.

### 14. `Car.get_braking_distance` silently ignores its argument once the car is dead

**Where:** [`simulation/car.py`](../src/umlsl_sim/simulation/car.py)
**Covered by:** `tests/test_simulation_car.py::TestBrakingDistance::test_a_dead_car_reports_its_speed_and_ignores_the_argument`

```python
if self.get_death_status():
    return self.speed          # ignores `speed`, and speed is 0 after death
```

A wreck reserving nothing beyond its body is reasonable; a function that
discards the argument it was given is the surprising part. No live caller
reaches it — `safety_checks.max_end_growth` tests for death first — so this is a
readability matter, not a bug. Left alone because changing what a wreck reserves
*is* a traffic-model change.

### 15. Crash attribution records only one of the two cars' directions

**Where:** [`simulation/traffic_environment.py`](../src/umlsl_sim/simulation/traffic_environment.py), `_execute_action`

```python
self.total_crashes += 1
self.crashes[car.direction] += 1     # `other_car.direction` is not counted
```

Both cars die, but only the acting car's direction is tallied, so
`sum(crashes.values()) == total_crashes` rather than `2 * total_crashes`. That
is self-consistent if `crashes` means "which direction *caused* the crash" and
wrong if it means "which directions were involved". The docstring does not say
which, and nothing reads it. A test pins the current relationship.

### 16. The RL history save format cannot carry an initial state, so `RLMode.LOAD_HISTORY` still cannot replay

**Where:** [`rl/rl_io.py`](../src/umlsl_sim/rl/rl_io.py) `create_game_history` / `load_game_history`, [`rl/training/rl_runner.py`](../src/umlsl_sim/rl/training/rl_runner.py) `_load_history`

This is the remaining half of finding **8**, and it sits **outside the
`factories` / `simulation` / `control` scope** I was asked to work in, so I have
flagged rather than changed it.

`create_game_history` pickles `(map, cars, actions)`, where `cars` are the live
`Car` objects **at the end of the episode**. `_load_history` then calls
`set_list_of_cars(car_history)` with no reservation book, so no snapshots are
taken and `replay` now raises `HistoryNotReplayable` with an explanation —
better than the old `AttributeError`, but still not a working replay.

A faithful replay is impossible from what is currently saved: the pickled cars
are in their final state, and their starting positions were never recorded.

**The change needed** (three lines, all in `rl/`): have `MlslEnv` capture
`game_model.game_history.car_snapshots` alongside the other history fields,
pickle it as a fourth object in `create_game_history`, restore it in
`load_game_history`, and assign it to `GameHistory.car_snapshots` in
`_load_history`. Say the word and I will make it.

### 17. `Car.get_adjacent_lane_segments` includes the car's own lane

**Where:** [`simulation/car.py`](../src/umlsl_sim/simulation/car.py)
**Covered by:** `tests/test_simulation_car.py::TestAdjacentLaneSegments::test_every_parallel_lane_is_listed_including_the_cars_own`

The name says "adjacent", and its singular sibling `get_adjacent_lane_segment`
takes a `lane_diff` and genuinely steps away. The plural returns *every* parallel
lane's segment, the car's own included. Its one caller,
`_choose_lane_change`, filters the car's own lane out immediately afterwards, so
the behaviour is correct — the name is just misleading. Renaming it to
`get_parallel_lane_segments` would cost one call site.

---

## Running the suite

```bash
cd UMLSL-Sim
pip install -e '.[dev]'
pytest tests -q                    # 687 tests, ~8s
pytest tests/integration -q        # full episodes on every bundled scenario
```

The unit tests need only the base install (`numpy`); nothing here requires the
`[rl]` extra. `manual_tests/` still holds the Stable-Baselines3 checks, which do.
