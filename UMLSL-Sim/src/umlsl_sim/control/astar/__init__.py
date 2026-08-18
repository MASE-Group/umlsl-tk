"""The NPC controller: A* route following.

`AstarCarController.get_action()` returns the (acceleration, lane change) that
follows the car's planned route without violating safety. It is the default
`simulation.ports.CarController`.
"""
