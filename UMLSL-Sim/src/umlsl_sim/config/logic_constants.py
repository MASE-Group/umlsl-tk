"""The traffic logic's own units: space, speed, acceleration, lane changes.

Everything here is expressed in the simulation's native length unit, the
*block*. A block is the side of one crossing cell and the width of one lane, and
the GUI happens to draw it as `BLOCK_SIZE` pixels, but no value below means
anything about a display: a headless run uses every one of them.
"""

# --- Space -------------------------------------------------------------------

# The simulation's length unit: one lane's width, one crossing cell's side.
BLOCK_SIZE = 40

# Extent of the world cars drive in. Road positions are given in this space, and
# an observation model normalises car coordinates against it.
WORLD_WIDTH = 40 * BLOCK_SIZE
WORLD_HEIGHT = 24 * BLOCK_SIZE

# Safety margin kept between a car and whatever is in front of it.
BUFFER = BLOCK_SIZE // 2

# --- Speed -------------------------------------------------------------------

LANE_MAX_SPEED = BLOCK_SIZE // 2
CROSSING_MAX_SPEED = LANE_MAX_SPEED // 2
MINIMAL_SPEED = CROSSING_MAX_SPEED // 2

MAX_ACC = BLOCK_SIZE // 4
MAX_DEC = BLOCK_SIZE // 4

# --- Manoeuvres --------------------------------------------------------------

# Lane-change encoding, shared by the car, both controllers and the RL action
# space; the numeric values are the ones the action space is built from. The
# RL action space maps index i to i - 1, so the four commands are contiguous
# from RIGHT_LANE_CHANGE upwards.
NO_LANE_CHANGE = 0
LEFT_LANE_CHANGE = 1
RIGHT_LANE_CHANGE = -1
# Give up a claim registered on an earlier tick and stay in the current lane.
# Only meaningful while a claim is pending and not yet committed; see
# `Car.change_lane` for the manoeuvre this belongs to.
WITHDRAW_CLAIM = 2

# A lane change runs in two phases, CLAIM_TIME + LANECHANGE_TIME_STEPS ticks
# in all:
#
# 1. *Claim* -- CLAIM_TIME ticks during which the target segment is only
#    claimed. The claim is registered without any collision check, and its
#    holder may withdraw it on any tick of this phase (and is expected to, once
#    it sees the claim overlap someone else's space). Other cars treat a claim
#    as taken space, but overlapping one is never a collision: nothing of the
#    car is on the target lane yet.
# 2. *Change* -- LANECHANGE_TIME_STEPS ticks after the claim turns itself into
#    a reservation. The reservation cannot be withdrawn, and the car lands on
#    the target lane at the end of it.
LANECHANGE_TIME_STEPS = 3
CLAIM_TIME = 2

# Look-ahead, in ticks, used when projecting a reservation forward.
JUMP_TIME_STEPS = 1

# A* congestion penalty: per-car multiplier on a crossing segment's time-cost,
# applied to (cars currently on the 4 crossing cells of the intersection +
# cars queued on its approach lane segments). 0 disables the penalty.
#
# It lives here rather than with the A* controller because the route search it
# tunes is part of the car itself (`Car.find_path`), which any controller --
# not only the A* one -- plans against.
ASTAR_CONGESTION_ALPHA = 0.25
