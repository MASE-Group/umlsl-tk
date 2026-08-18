"""Constants that only matter because something is being drawn.

The window is a 1:1 view of the world coordinate space defined in
`config.logic_constants`, so the window size is derived from it rather than
restated here; everything else below (frame pacing, lane-line offsets) has no
meaning in a headless run.
"""

from umlsl_sim.config.logic_constants import WORLD_HEIGHT, WORLD_WIDTH

# The scene is drawn at one pixel per world unit, so the window is exactly as
# large as the world. A view that zoomed or panned would scale here instead.
WINDOW_WIDTH = WORLD_WIDTH
WINDOW_HEIGHT = WORLD_HEIGHT

# Frames per second the windows redraw at, and the period of the flashing used
# to highlight reservations, in frames.
TIME_PER_FRAME = 60
FLASH_CYCLE = 60 * TIME_PER_FRAME

# Offset, in pixels, between a lane's nominal edge and the line drawn for it.
LANE_DISPLACEMENT = 2
