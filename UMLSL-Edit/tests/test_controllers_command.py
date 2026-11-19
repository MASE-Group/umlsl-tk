import unittest
from unittest.mock import Mock, patch

from umlsl_edit.controllers.command_controller import CommandController
from umlsl_edit.model.entities.road import Road, RoadOrientation, RoadParams


class TestCommandController(unittest.TestCase):

    def setUp(self):
        self.reader = Mock()
        self.writer = Mock()
        self.settings = Mock()
        self.umlsl = Mock()
        self.controller = CommandController(self.reader, self.writer, self.umlsl, self.settings)

    def test_init(self):
        self.assertEqual(self.controller.traffic_snapshot_reader, self.reader)
        self.assertEqual(self.controller.traffic_snapshot_writer, self.writer)
        self.assertEqual(self.controller.umlsl_queries_model, self.umlsl)
        self.assertEqual(self.controller.settings_model, self.settings)

    @patch('umlsl_edit.controllers.command_controller.add_car.AddCarCommand')
    @patch.object(CommandController, '_execute_command')
    def test_add_car(self, mock_execute, mock_command):
        params = RoadParams(
            name="Main",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=1,
        )
        road = Road.from_params(params)
        mock_command_instance = Mock()
        mock_command.return_value = mock_command_instance

        self.controller.add_car("Car1", road, 0, "#ff0000", 10.0, 0.0, 5.0, 4.0, 0.0, None)

        mock_command.assert_called_once()
        # Check the call arguments
        args, kwargs = mock_command.call_args
        self.assertEqual(args[0], self.reader)
        self.assertEqual(args[1], self.writer)
        self.assertEqual(args[2], self.settings)
        # car_params would be checked, but it's complex

        mock_execute.assert_called_once_with(mock_command_instance)

    def test_change_braking_acceleration_updates_settings(self):
        self.controller.change_braking_acceleration(6.5)

        self.settings.set_braking_acceleration.assert_called_once_with(6.5)

    def test_change_max_speed_updates_settings(self):
        self.controller.change_max_speed(20.0)

        self.settings.set_max_speed.assert_called_once_with(20.0)

    def test_settings_changes_do_not_mark_snapshot_unsaved(self):
        # Settings are not part of the saved snapshot file, so changing them
        # must not trigger an "unsaved changes" prompt.
        self.controller.change_braking_acceleration(6.5)
        self.controller.change_max_speed(20.0)

        self.assertFalse(self.controller.get_data_changed_since_last_save())


if __name__ == "__main__":
    unittest.main()
