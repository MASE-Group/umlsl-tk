"""The model creators: turn descriptions into the objects a simulation runs on.

Input:  a road network, plus either a `CarSpec` (a predefined car -- the
        description type is defined here and filled in by the scenario parser)
        or nothing at all (a random one).
Output: `Car` objects placed on free lane segments with their reservations
        registered, and the `Segment` graph that a road network is driven on.

The factories sit above the simulation layer and below anything that runs it:
they know how a car is *built*, while `simulation` knows how one *behaves*. A
different placement policy -- clustered traffic, a fixed grid, a replayed
recording -- is a replacement for this module and nothing else.
"""

from umlsl_sim.factories.car_spec import CarSpec, resolve_position
from umlsl_sim.factories.create_cars import (
    create_goal,
    create_predefined_car,
    create_random_car,
    total_lane_segments,
)
from umlsl_sim.factories.create_segments import create_segments

__all__ = [
    "CarSpec",
    "resolve_position",
    "create_goal",
    "create_predefined_car",
    "create_random_car",
    "total_lane_segments",
    "create_segments",
]
