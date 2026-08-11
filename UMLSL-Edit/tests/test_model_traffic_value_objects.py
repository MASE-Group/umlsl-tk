import unittest

from umlsl_edit.model.traffic_value_objects.lane import Lane
from umlsl_edit.model.traffic_value_objects.turn_intent import TurnIntent, TurnDirection


class TestTurnIntent(unittest.TestCase):

    def test_turn_intent_creation_valid(self):
        lane = Lane(lane_index=0, road_uid="road-1")
        intent = TurnIntent(direction=TurnDirection.LEFT, target_lane=lane)
        self.assertEqual(intent.direction, TurnDirection.LEFT)
        self.assertEqual(intent.target_lane, lane)

    def test_turn_intent_invalid_direction(self):
        lane = Lane(lane_index=0, road_uid="road-1")
        with self.assertRaises(ValueError):
            TurnIntent(direction="invalid", target_lane=lane)

    def test_turn_intent_invalid_target_lane(self):
        with self.assertRaises(ValueError):
            TurnIntent(direction=TurnDirection.RIGHT, target_lane="invalid")


if __name__ == "__main__":
    unittest.main()
