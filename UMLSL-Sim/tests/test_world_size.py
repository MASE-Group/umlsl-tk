"""The size of the world a scenario runs in, and how a window shows a world of any size."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from umlsl_sim.config.logic_constants import BLOCK_SIZE, DEFAULT_WORLD_SIZE, WORLD_HEIGHT, WORLD_WIDTH
from umlsl_sim.gui.camera import MAX_BLOCK_PIXELS, MIN_ZOOM, Camera
from umlsl_sim.scenario import loader
from umlsl_sim.scenario.loader import available_scenarios, load_scenario, world_size_of
from umlsl_sim.simulation.road_network.road_network import Road
from umlsl_sim.simulation.traffic_environment import TrafficEnv


def ring(width: int, height: int):
    """The four one-lane border roads of a ``width`` x ``height`` px world."""
    return [
        Road("bottom", True, 0, 1, 0),
        Road("right", False, width - BLOCK_SIZE, 0, 1),
        Road("top", True, height - BLOCK_SIZE, 0, 1),
        Road("left", False, 0, 1, 0),
    ]


class TestScenarioWorldSize(unittest.TestCase):
    def test_a_scenario_without_a_size_has_the_default_world(self):
        self.assertEqual(world_size_of({}), (WORLD_WIDTH, WORLD_HEIGHT))

    def test_every_bundled_scenario_keeps_the_world_its_models_were_trained_on(self):
        for key in available_scenarios():
            with self.subTest(key):
                self.assertEqual(load_scenario(key)["world_size"], DEFAULT_WORLD_SIZE)

    def test_a_stated_size_is_read(self):
        self.assertEqual(world_size_of({"width": 4560, "height": 2400}), (4560, 2400))

    def test_a_size_must_be_a_positive_whole_number_of_pixels(self):
        for bad in (0, -40, 12.5, "1600", True):
            with self.subTest(bad), self.assertRaises(ValueError):
                world_size_of({"width": bad})

    def test_load_scenario_returns_the_size(self):
        data = {"name": "BIG", "scenario_name": "big", "players": 1, "width": 4000, "height": 2000,
                "roads": [{"name": r.name, "horizontal": r.horizontal, "top": r.top, "right": len(r.right_lanes),
                           "left": len(r.left_lanes)} for r in ring(4000, 2000)]}
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "big.json").write_text(json.dumps(data))
            with patch.object(loader, "_DATA_DIR", Path(folder)):
                scenario = load_scenario("big")
        self.assertEqual(scenario["world_size"], (4000, 2000))


class TestTrafficEnvWorldSize(unittest.TestCase):
    def test_the_default_world(self):
        self.assertEqual(TrafficEnv(roads=ring(*DEFAULT_WORLD_SIZE), players=1).world_size, DEFAULT_WORLD_SIZE)

    def test_a_larger_world_runs_like_any_other(self):
        env = TrafficEnv(roads=ring(4000, 2000), players=3, world_size=(4000, 2000))
        env.reset()
        for _ in range(200):
            env.play_step()
        self.assertEqual(env.world_size, (4000, 2000))
        self.assertEqual(env.game_history.world_size, (4000, 2000))

    def test_a_road_outside_the_world_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Road 'right'"):
            TrafficEnv(roads=ring(4000, 960), players=1)  # the default world is 1600 px wide


@unittest.skipUnless(importlib.util.find_spec("gymnasium"), "needs the [rl] extra")
class TestObservationNormalisation(unittest.TestCase):
    def observe(self, world_size):
        from umlsl_sim.rl.observations.numeric_observation import NumbericObservation

        env = TrafficEnv(roads=ring(*world_size), players=2, with_agent=True, world_size=world_size)
        env.reset()
        observation = NumbericObservation(env)
        return env, observation, observation.observe()

    def test_goal_deltas_are_relative_to_the_world(self):
        for world_size in (DEFAULT_WORLD_SIZE, (4000, 2000)):
            with self.subTest(world_size):
                env, _, values = self.observe(world_size)
                agent = env.agent_car
                self.assertAlmostEqual(float(values[0]), (agent.goal.pos.x - agent.pos.x) / world_size[0], places=6)
                self.assertAlmostEqual(float(values[1]), (agent.goal.pos.y - agent.pos.y) / world_size[1], places=6)


class TestCamera(unittest.TestCase):
    VIEWPORT = (100.0, 50.0, 800.0, 600.0)

    def test_the_fitted_view_shows_the_whole_world_centred(self):
        camera = Camera()
        scale, ox, oy = camera.transform(self.VIEWPORT, (1600, 960))
        self.assertAlmostEqual(scale, 0.5)  # 800 / 1600 < 600 / 960
        self.assertAlmostEqual(ox, 100.0)
        self.assertAlmostEqual(oy + 960 * scale / 2, 50.0 + 300.0)  # centred vertically

    def test_a_larger_world_gets_fewer_pixels_per_block(self):
        camera = Camera()
        small = camera.scale(self.VIEWPORT, (1600, 960))
        large = camera.scale(self.VIEWPORT, (4800, 2880))
        self.assertAlmostEqual(small / large, 3.0)

    def test_zooming_keeps_the_point_under_the_mouse(self):
        camera = Camera()
        world = (1600, 960)
        before = camera.to_world(self.VIEWPORT, world, 300.0, 200.0)
        camera.zoom_at(self.VIEWPORT, world, 300.0, 200.0, 2.0)
        after = camera.to_world(self.VIEWPORT, world, 300.0, 200.0)
        self.assertAlmostEqual(before[0], after[0])
        self.assertAlmostEqual(before[1], after[1])
        self.assertAlmostEqual(camera.zoom, 2.0)

    def test_zooming_out_is_bounded_only_to_keep_the_view_sane(self):
        camera = Camera()
        for _ in range(200):
            camera.zoom_at(self.VIEWPORT, (1600, 960), 500.0, 350.0, 0.5)
        self.assertAlmostEqual(camera.zoom, MIN_ZOOM)

    def test_zooming_in_stops_at_a_readable_block(self):
        camera = Camera()
        for _ in range(200):
            camera.zoom_at(self.VIEWPORT, (1600, 960), 500.0, 350.0, 2.0)
        self.assertAlmostEqual(camera.scale(self.VIEWPORT, (1600, 960)) * BLOCK_SIZE, MAX_BLOCK_PIXELS)

    def test_panning_moves_the_world_with_the_mouse_and_reset_fits_again(self):
        camera = Camera()
        world = (1600, 960)
        before = camera.transform(self.VIEWPORT, world)
        camera.pan(self.VIEWPORT, world, 40.0, -20.0)
        after = camera.transform(self.VIEWPORT, world)
        self.assertAlmostEqual(after[1] - before[1], 40.0)
        self.assertAlmostEqual(after[2] - before[2], -20.0)
        camera.reset()
        self.assertTrue(camera.is_fitted)
        self.assertEqual(camera.transform(self.VIEWPORT, world), before)


class TestSavedScenarioKeepsItsWorld(unittest.TestCase):
    def test_the_saved_file_states_the_world_size(self):
        from umlsl_sim.gui.control.scenario_saver import save_current_scenario

        env = TrafficEnv(roads=ring(4000, 2000), players=3, world_size=(4000, 2000))
        env.reset()
        for _ in range(20):
            env.play_step()
        with tempfile.TemporaryDirectory() as folder:
            path = save_current_scenario(env, "wide", out_dir=Path(folder)).path
            data = json.loads(path.read_text())
        self.assertEqual((data["width"], data["height"]), (4000, 2000))
        self.assertEqual(world_size_of(data), (4000, 2000))


if __name__ == "__main__":
    unittest.main()
