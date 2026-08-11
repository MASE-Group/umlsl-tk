import unittest

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.helpers.event_types import SettingsEventType
from umlsl_edit.model.helpers.observables import (
    Observable,
    ObservableDict,
    ReadOnlyMergedDictView,
)


class TestObservable(unittest.TestCase):
    def test_attach_notify_and_detach(self):
        observable = Observable()
        received = []

        def observer(event_type, data):
            received.append((event_type, data))

        observable.attach(observer)
        observable.notify("event", {"payload": 1})
        self.assertEqual(received, [("event", {"payload": 1})])

        observable.detach(observer)
        observable.notify("event", {"payload": 2})
        self.assertEqual(received, [("event", {"payload": 1})])

    def test_attach_does_not_duplicate(self):
        observable = Observable()
        received = []

        def observer(event_type, data):
            received.append((event_type, data))

        observable.attach(observer)
        observable.attach(observer)
        observable.notify("event", None)

        self.assertEqual(len(received), 1)


class TestObservableDict(unittest.TestCase):
    def test_add_update_remove_callbacks(self):
        events = []

        def on_add(value):
            events.append(("add", value))

        def on_update(value):
            events.append(("update", value))

        def on_remove(value):
            events.append(("remove", value))

        obs = ObservableDict(on_add=on_add, on_remove=on_remove, on_update=on_update)

        obs["a"] = 1
        obs["a"] = 2
        del obs["a"]

        self.assertEqual(events, [("add", 1), ("update", 2), ("remove", 2)])

    def test_iter_len_getitem(self):
        obs = ObservableDict(initial_data={"a": 1, "b": 2})
        self.assertEqual(len(obs), 2)
        self.assertEqual(obs["a"], 1)
        self.assertEqual(sorted(list(iter(obs))), ["a", "b"])

    def test_add_operator_merges(self):
        left = ObservableDict(initial_data={"a": 1})
        right = ObservableDict(initial_data={"b": 2})
        merged = left + right
        self.assertEqual(merged["a"], 1)
        self.assertEqual(merged["b"], 2)


class TestReadOnlyMergedDictView(unittest.TestCase):
    def test_merge_lookup_and_contains(self):
        d1 = ObservableDict(initial_data={"a": 1, "shared": "first"})
        d2 = ObservableDict(initial_data={"b": 2, "shared": "second"})
        view = ReadOnlyMergedDictView([d1, d2])

        self.assertEqual(view["a"], 1)
        self.assertEqual(view["b"], 2)
        self.assertEqual(view["shared"], "second")
        self.assertIn("a", view)
        self.assertIn("shared", view)

    def test_keys_values_items(self):
        d1 = ObservableDict(initial_data={"a": 1})
        d2 = ObservableDict(initial_data={"b": 2})
        view = ReadOnlyMergedDictView([d1, d2])

        self.assertEqual(set(view.keys()), {"a", "b"})
        self.assertEqual(set(view.values()), {1, 2})
        self.assertEqual(set(view.items()), {("a", 1), ("b", 2)})


class TestSettingsModel(unittest.TestCase):
    def test_set_braking_acceleration_notifies(self):
        settings = SettingsModel(braking_acceleration=4.0, max_speed=10.0)
        received = []

        def observer(event_type, data):
            received.append((event_type, data))

        settings.attach(observer)
        settings.set_braking_acceleration(2.5)

        self.assertEqual(settings.braking_acceleration, 2.5)
        self.assertEqual(received, [(SettingsEventType.CHANGE_BRAKING_DECELERATION, 2.5)])

    def test_set_max_speed_notifies(self):
        settings = SettingsModel(braking_acceleration=4.0, max_speed=10.0)
        received = []

        def observer(event_type, data):
            received.append((event_type, data))

        settings.attach(observer)
        settings.set_max_speed(12.0)

        self.assertEqual(settings.max_speed, 12.0)
        self.assertEqual(received, [(SettingsEventType.CHANGE_MAX_SPEED, 12.0)])

    def test_braking_distance_calculation(self):
        settings = SettingsModel(braking_acceleration=2.0, max_speed=10.0)
        self.assertEqual(settings.braking_distance(), 25.0)


if __name__ == "__main__":
    unittest.main()
