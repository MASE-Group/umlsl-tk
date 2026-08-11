import unittest
from unittest.mock import MagicMock, patch

from umlsl_edit.commands.roads.add_road import AddRoadCommand
from umlsl_edit.commands.roads.delete_road import DeleteRoad
from umlsl_edit.commands.roads.edit_road import EditRoadCommand
from umlsl_edit.model.entities.road import RoadParams, RoadOrientation
from umlsl_edit.model.errors.road_errors import RoadValidationError


class TestAddRoadCommand(unittest.TestCase):
    def test_execute_validates_and_adds_road(self):
        reader = MagicMock()
        writer = MagicMock()
        road_params = RoadParams(
            name="Main",
            orientation=RoadOrientation.HORIZONTAL,
            position=10.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=1,
        )

        with patch(
            "umlsl_edit.commands.roads.add_road.Road.from_params",
            autospec=True,
        ) as from_params:
            road_instance = MagicMock()
            from_params.return_value = road_instance

            cmd = AddRoadCommand(reader, writer, road_params)
            cmd.execute()

            reader.validate_road_params.assert_called_once_with(road_params, True)
            from_params.assert_called_once_with(road_params)
            writer.add_road.assert_called_once_with(road_instance)


class TestEditRoadCommand(unittest.TestCase):
    def test_execute_raises_when_road_missing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_road_existing.return_value = False
        road_params = MagicMock(spec=RoadParams)

        cmd = EditRoadCommand(reader, writer, road_params, uid="road-1")

        with self.assertRaises(RoadValidationError):
            cmd.execute()

        reader.validate_road_params.assert_not_called()
        writer.update_road.assert_not_called()

    def test_execute_updates_road_when_existing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_road_existing.return_value = True
        road_params = MagicMock(spec=RoadParams)

        cmd = EditRoadCommand(reader, writer, road_params, uid="road-1")
        cmd.execute()

        reader.validate_road_params.assert_called_once_with(road_params, False, "road-1")
        writer.update_road.assert_called_once_with("road-1", road_params)


class TestDeleteRoadCommand(unittest.TestCase):
    def test_execute_raises_when_road_missing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.get_road_by_uid.side_effect = ValueError("missing")

        cmd = DeleteRoad(writer, reader, road_uid="road-1")

        with self.assertRaises(RoadValidationError):
            cmd.execute()

        writer.remove_road.assert_not_called()

    def test_execute_removes_when_existing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.get_road_by_uid.return_value = MagicMock()

        cmd = DeleteRoad(writer, reader, road_uid="road-1")
        cmd.execute()

        writer.remove_road.assert_called_once_with("road-1")


if __name__ == "__main__":
    unittest.main()
