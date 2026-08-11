import unittest
from unittest.mock import Mock

from umlsl_edit.controllers.data_controller import DataController
from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnDirection


class TestDataController(unittest.TestCase):

    def setUp(self):
        self.reader = Mock()
        self.controller = DataController(self.reader)

    def test_init(self):
        self.assertEqual(self.controller._traffic_snapshot_reader, self.reader)

    def test_replace_snapshot_reader(self):
        new_reader = Mock()
        self.controller.replace_snapshot_reader(new_reader)
        self.assertEqual(self.controller._traffic_snapshot_reader, new_reader)

    def test_get_all_cars(self):
        cars = {"car1": Mock()}
        self.reader.get_cars.return_value = cars
        result = self.controller.get_all_cars()
        self.assertEqual(result, cars)
        self.reader.get_cars.assert_called_once()

    def test_get_all_roads(self):
        roads = {"road1": Mock()}
        self.reader.get_roads.return_value = roads
        result = self.controller.get_all_roads()
        self.assertEqual(result, roads)
        self.reader.get_roads.assert_called_once()

    def test_get_road_by_uid(self):
        road = Mock()
        self.reader.get_road_by_uid.return_value = road
        result = self.controller.get_road_by_uid("road1")
        self.assertEqual(result, road)
        self.reader.get_road_by_uid.assert_called_once_with("road1")

    def test_get_valid_turn_intent_lanes(self):
        lanes = [Lane(lane_index=0, road_uid="road1")]
        self.reader.get_valid_turn_intent_lanes.return_value = lanes
        lane = Lane(lane_index=0, road_uid="road1")
        result = self.controller.get_valid_turn_intent_lanes(10.0, 5.0, lane, 4.0, TurnDirection.LEFT)
        self.assertEqual(result, lanes)
        self.reader.get_valid_turn_intent_lanes.assert_called_once_with(10.0, 5.0, lane, 4.0, TurnDirection.LEFT)


if __name__ == "__main__":
    unittest.main()
