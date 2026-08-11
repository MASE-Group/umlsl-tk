import unittest
from unittest.mock import Mock

from umlsl_edit.controllers.event_controller import EventController


class TestEventController(unittest.TestCase):

    def test_init_sets_attributes_and_sets_up_listeners(self):
        view = Mock()
        traffic_snapshot = Mock()
        settings = Mock()
        umlsl_queries = Mock()

        controller = EventController(view, traffic_snapshot, settings, umlsl_queries)

        self.assertEqual(controller._view, view)
        self.assertEqual(controller._traffic_snapshot, traffic_snapshot)
        self.assertEqual(controller._settings, settings)
        self.assertEqual(controller._umlsl_queries, umlsl_queries)

        traffic_snapshot.attach.assert_called_once()
        settings.attach.assert_called_once()
        umlsl_queries.attach.assert_called_once()

    def test_replace_models(self):
        view = Mock()
        traffic_snapshot = Mock()
        settings = Mock()
        umlsl_queries = Mock()

        controller = EventController(view, traffic_snapshot, settings, umlsl_queries)

        new_traffic_snapshot = Mock()
        new_umlsl_queries = Mock()

        controller.replace_models(new_traffic_snapshot, new_umlsl_queries)

        self.assertEqual(controller._traffic_snapshot, new_traffic_snapshot)
        self.assertEqual(controller._umlsl_queries, new_umlsl_queries)

        # Check that new listeners are set up
        new_traffic_snapshot.attach.assert_called_once()
        new_umlsl_queries.attach.assert_called_once()


if __name__ == "__main__":
    unittest.main()
