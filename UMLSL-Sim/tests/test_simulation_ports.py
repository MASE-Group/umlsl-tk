"""Unit tests for `simulation.ports` -- the interfaces the layer is driven through.

The point of this module is that nothing below the composition root names a
concrete controller or renderer. These tests hold that line: a plain object with
the right methods satisfies each protocol, and a headless run is the same runner
with a different renderer rather than a special case.
"""

import unittest

from umlsl_sim.config.render_mode import RenderMode
from umlsl_sim.simulation import ports
from umlsl_sim.simulation.ports import (
    CarController,
    NullRenderer,
    Renderer,
    create_renderer,
    set_renderer_factory,
)


class _StubRenderer:
    """A renderer built from nothing but the methods the protocol names."""

    def __init__(self):
        self.paused = False
        self.bound = None
        self.frames = 0
        self.closed = False

    def bind(self, cars, roads, reservation_management=None):
        self.bound = (cars, roads, reservation_management)

    def draw_frame(self):
        self.frames += 1

    def run_loop(self, update, interval=None):
        update(interval or 0.0)

    def stop_loop(self):
        pass

    def close(self):
        self.closed = True


class TestCarControllerProtocol(unittest.TestCase):

    def test_anything_with_get_action_satisfies_it(self):
        class Stub:
            def get_action(self):
                return (0, 0)

        self.assertIsInstance(Stub(), CarController)

    def test_an_object_without_get_action_does_not(self):
        self.assertNotIsInstance(object(), CarController)

    def test_no_inheritance_is_required(self):
        class Stub:
            def get_action(self):
                return (1, -1)

        self.assertNotIn(CarController, type(Stub()).__mro__)
        self.assertIsInstance(Stub(), CarController)


class TestRendererProtocol(unittest.TestCase):

    def test_a_stub_with_every_method_satisfies_it(self):
        self.assertIsInstance(_StubRenderer(), Renderer)

    def test_the_null_renderer_satisfies_it(self):
        self.assertIsInstance(NullRenderer(), Renderer)

    def test_a_partial_implementation_does_not(self):
        class Partial:
            paused = False

            def bind(self, cars, roads, reservation_management=None):
                pass

        self.assertNotIsInstance(Partial(), Renderer)


class TestNullRenderer(unittest.TestCase):

    def setUp(self):
        self.renderer = NullRenderer()

    def test_it_starts_unpaused(self):
        self.assertFalse(self.renderer.paused)

    def test_binding_and_drawing_do_nothing_observable(self):
        self.assertIsNone(self.renderer.bind([], []))
        self.assertIsNone(self.renderer.draw_frame())

    def test_bind_accepts_the_optional_reservation_book(self):
        self.assertIsNone(self.renderer.bind([], [], None))

    def test_the_loop_runs_until_it_is_stopped(self):
        ticks = []

        def update(dt):
            ticks.append(dt)
            if len(ticks) == 5:
                self.renderer.stop_loop()

        self.renderer.run_loop(update)
        self.assertEqual(len(ticks), 5)

    def test_an_unspecified_interval_means_no_delay(self):
        seen = []

        def update(dt):
            seen.append(dt)
            self.renderer.stop_loop()

        self.renderer.run_loop(update)
        self.assertEqual(seen, [0.0])

    def test_an_explicit_interval_is_handed_to_the_update(self):
        seen = []

        def update(dt):
            seen.append(dt)
            self.renderer.stop_loop()

        self.renderer.run_loop(update, interval=0.25)
        self.assertEqual(seen, [0.25])

    def test_closing_also_ends_the_loop(self):
        ticks = []

        def update(dt):
            ticks.append(dt)
            self.renderer.close()

        self.renderer.run_loop(update)
        self.assertEqual(len(ticks), 1)

    def test_close_is_safe_to_call_more_than_once(self):
        self.renderer.close()
        self.renderer.close()

    def test_paused_is_writable_because_the_runners_write_it(self):
        self.renderer.paused = True
        self.assertTrue(self.renderer.paused)


class TestRendererFactory(unittest.TestCase):

    def setUp(self):
        self._original = ports._renderer_factory
        self.addCleanup(set_renderer_factory, self._original)

    def test_the_default_factory_serves_headless_runs(self):
        set_renderer_factory(ports._null_renderer_factory)
        self.assertIsInstance(create_renderer(RenderMode.NO_GUI), NullRenderer)

    def test_the_default_factory_refuses_a_gui_it_cannot_build(self):
        set_renderer_factory(ports._null_renderer_factory)
        with self.assertRaises(RuntimeError) as ctx:
            create_renderer(RenderMode.GUI)
        self.assertIn("no renderer factory is registered", str(ctx.exception))

    def test_a_registered_factory_is_used_instead(self):
        stub = _StubRenderer()
        set_renderer_factory(lambda mode, show: stub)
        self.assertIs(create_renderer(RenderMode.GUI), stub)
        self.assertIs(create_renderer(RenderMode.NO_GUI), stub)

    def test_the_mode_and_flag_are_passed_through(self):
        calls = []

        def factory(mode, show_reservations):
            calls.append((mode, show_reservations))
            return _StubRenderer()

        set_renderer_factory(factory)
        create_renderer(RenderMode.GUI, show_reservations=False)
        self.assertEqual(calls, [(RenderMode.GUI, False)])

    def test_reservations_are_shown_by_default(self):
        calls = []
        set_renderer_factory(lambda mode, show: calls.append(show) or _StubRenderer())
        create_renderer(RenderMode.NO_GUI)
        self.assertEqual(calls, [True])

    def test_registering_replaces_the_previous_factory(self):
        first, second = _StubRenderer(), _StubRenderer()
        set_renderer_factory(lambda mode, show: first)
        set_renderer_factory(lambda mode, show: second)
        self.assertIs(create_renderer(RenderMode.NO_GUI), second)


class TestRenderMode(unittest.TestCase):

    def test_the_two_modes_are_truthy_and_falsy(self):
        self.assertTrue(RenderMode.GUI.value)
        self.assertFalse(RenderMode.NO_GUI.value)


if __name__ == "__main__":
    unittest.main()
