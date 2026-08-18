"""How a *run* of the traffic logic is scored and brought to an end.

These are episode-level knobs: they say nothing about how a car moves, only
about when a simulation declares a winner, hands a crossing claim on, or gives
up on a jam. Anything that changes the driving model itself belongs in
`logic_constants`.
"""

from umlsl_sim.config.logic_constants import BLOCK_SIZE, CROSSING_MAX_SPEED

# Goals a car must reach to win.
WINNING_SCORE = 100

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

# Number of consecutive frames on which every living car must stand still
# before the environment reports a deadlock. A single such frame is not
# evidence of one: dense traffic brings every car to a halt for a tick or two
# while a crossing claim is reordered or withdrawn, and then moves on again.
# Only a stall that outlasts this window is reported.
#
# The window therefore has to outlast the recovery it exists to allow. A
# stalled claim is not withdrawn until PRIORITY_WITHDRAW_TICKS ticks without
# progress, and the car it was holding up then needs a tick to claim the
# intersection and another to get going, so a window shorter than that would
# always cut the stall off before the lease had a chance to break it. Derive it
# from the lease bound rather than fixing a number that has to be kept in step
# with it by hand.
DEADLOCK_FRAMES = PRIORITY_WITHDRAW_TICKS + CROSSING_TRAVERSAL_TICKS
