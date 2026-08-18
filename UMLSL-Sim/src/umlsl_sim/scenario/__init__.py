"""The scenario parser: JSON files in, a runnable world description out.

Input:  a scenario key naming one of the bundled files in `scenario/scenarios/`.
Output: a dict of `roads`, `players`, `scenario_name` and `predefined_cars`
        (`CarSpec` objects -- the description type belongs to
        `umlsl_sim.factories`, which builds cars from them),
        which is exactly the keyword set `umlsl_sim.app.main.main` takes -- so
        `main(**load_scenario("two_crossings"), ...)` is the whole contract.

Replacing this module means providing `available_scenarios()` and
`load_scenario(key)` with those return shapes; no consumer parses JSON itself,
and nothing here knows how a road is simulated or drawn.
"""

from umlsl_sim.scenario.loader import available_scenarios, load_scenario

__all__ = ["available_scenarios", "load_scenario"]
