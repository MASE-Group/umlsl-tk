"""The traffic logic: roads, cars, reservations, and the tick that advances them.

This is the layer everything else is built on, and it depends on nothing but
`umlsl_sim.config`, `umlsl_sim.factories` and `umlsl_sim.palettes`. It has no
idea whether a run is watched, whether an agent is learning from it, or what
decides an NPC's next move -- those arrive through `simulation.ports`.

The pieces:

* `road_network` -- roads, lanes, segments, crossings: the world's geometry.
* `car` -- one vehicle's state, its route search, and how it moves.
* `reservations` -- who has claimed which space, and who may cross next.
* `traffic_environment` -- `TrafficEnv`, the tick: collect every car's action,
  apply it, detect crashes, goals and deadlock. This is the module a new front
  end or a new learner is written against.
* `episode_history` -- a recorded run, replayable through any `Renderer`.
* `safety_checks`, `event_checks` -- the predicates the above are phrased in.
* `ports` -- the interfaces the layer is driven through: `CarController` and
  `Renderer`.
"""
