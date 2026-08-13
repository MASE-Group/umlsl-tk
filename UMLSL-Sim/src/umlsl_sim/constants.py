# Size
BLOCK_SIZE = 40
LANE_DISPLACEMENT = 2
WINDOW_WIDTH = 40 * BLOCK_SIZE
WINDOW_HEIGHT = 24 * BLOCK_SIZE
BUFFER = BLOCK_SIZE // 2

LANE_MAX_SPEED = BLOCK_SIZE // 2
CROSSING_MAX_SPEED = LANE_MAX_SPEED // 2
MINIMAL_SPEED = CROSSING_MAX_SPEED // 2

WINNING_SCORE = 100

# GUI Only
TIME_PER_FRAME = 60 
FLASH_CYCLE = 60 * TIME_PER_FRAME

LANECHANGE_TIME_STEPS = 3
CLAIMTIME = 5

MAX_ACC = BLOCK_SIZE // 4
MAX_DEC = BLOCK_SIZE // 4
JUMP_TIME_STEPS = 1

# lane change
NO_LANE_CHANGE = 0
LEFT_LANE_CHANGE = 1
RIGHT_LANE_CHANGE = -1

# A* congestion penalty: per-car multiplier on a crossing segment's time-cost,
# applied to (cars currently on the 4 crossing cells of the intersection +
# cars queued on its approach lane segments). 0 disables the penalty.
ASTAR_CONGESTION_ALPHA = 0.25

# Crossing-claim lease (see IntersectionState). A claim on an intersection is
# held only while its claimant keeps moving; a claimant that stalls is first
# reordered behind the cars still approaching normally, and then loses the
# claim altogether. Both bounds are in ticks and scaled to the time it takes to
# drive one crossing segment at the crossing speed limit, so a car waiting its
# legitimate turn behind traffic that is genuinely crossing is not mistaken for
# a stalled one. Raising them towards infinity recovers the original behaviour,
# in which a claim once taken was never given up.
CROSSING_TRAVERSAL_TICKS = BLOCK_SIZE // CROSSING_MAX_SPEED
PRIORITY_REORDER_TICKS = CROSSING_TRAVERSAL_TICKS
PRIORITY_WITHDRAW_TICKS = 3 * CROSSING_TRAVERSAL_TICKS

# Number of consecutive frames on which every car must stand still before the
# environment reports a deadlock. A single such frame is not evidence of one:
# dense traffic brings every car to a halt for a tick or two while a crossing
# claim is reordered or withdrawn, and then moves on again. Only a stall that
# outlasts this window is reported.
DEADLOCK_FRAMES = 10
