from enum import Enum


class Direction(Enum):
    UP = (0, 1)
    DOWN = (0, -1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def opposite(self):
        """Returns the opposite direction of the current one."""
        if self == Direction.UP: return Direction.DOWN
        if self == Direction.DOWN: return Direction.UP
        if self == Direction.LEFT: return Direction.RIGHT
        if self == Direction.RIGHT: return Direction.LEFT
        return None
