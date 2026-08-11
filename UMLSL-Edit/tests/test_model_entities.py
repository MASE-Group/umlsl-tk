import unittest

from umlsl_edit.model.entities.road import Road, RoadOrientation, RoadParams
from umlsl_edit.model.errors.road_errors import RoadValidationError
from umlsl_edit.model.traffic_value_objects.lane import Lane, LaneDirection
from umlsl_edit.model.entities.car import CarParams


class DummyTrafficSnapshotReader:
    def __init__(self, road, lane_width=3.5):
        self._road = road
        self._lane_width = lane_width

    def get_road_by_uid(self, road_uid: str):
        if road_uid != self._road.uid:
            raise ValueError("Road not found")
        return self._road

    def get_lane_width(self):
        return self._lane_width


class TestLane(unittest.TestCase):
    def test_lane_validation(self):
        Lane(lane_index=0, road_uid="road-1")
        with self.assertRaises(ValueError):
            Lane(lane_index="0", road_uid="road-1")
        with self.assertRaises(ValueError):
            Lane(lane_index=0, road_uid=123)

    def test_lane_name_and_direction(self):
        road = Road.from_params(
            RoadParams(
                name="Main",
                orientation=RoadOrientation.HORIZONTAL,
                position=0.0,
                number_of_forward_lanes=1,
                number_of_backward_lanes=1,
            )
        )
        reader = DummyTrafficSnapshotReader(road)

        lane_forward = Lane(lane_index=0, road_uid=road.uid)
        lane_backward = Lane(lane_index=-1, road_uid=road.uid)

        self.assertEqual(lane_forward.get_name(reader), "r1")
        self.assertEqual(lane_backward.get_name(reader), "l1")

        self.assertEqual(lane_forward.get_direction(), LaneDirection.FORWARD)
        self.assertEqual(lane_backward.get_direction(), LaneDirection.BACKWARD)
        self.assertTrue(lane_forward.is_forward())
        self.assertFalse(lane_backward.is_forward())

    def test_get_one_dimensional_position_horizontal(self):
        road = Road.from_params(
            RoadParams(
                name="Main",
                orientation=RoadOrientation.HORIZONTAL,
                position=100.0,
                number_of_forward_lanes=2,
                number_of_backward_lanes=2,
            )
        )
        reader = DummyTrafficSnapshotReader(road, lane_width=3.0)

        forward_lane = road.forward_lanes[0]  # lane_index = 0
        backward_lane = road.backward_lanes[0]  # lane_index = -1

        self.assertEqual(forward_lane.get_one_dimensional_position(reader), 100.0)
        self.assertEqual(backward_lane.get_one_dimensional_position(reader), 103.0)

    def test_get_one_dimensional_position_vertical(self):
        road = Road.from_params(
            RoadParams(
                name="Main",
                orientation=RoadOrientation.VERTICAL,
                position=50.0,
                number_of_forward_lanes=2,
                number_of_backward_lanes=2,
            )
        )
        reader = DummyTrafficSnapshotReader(road, lane_width=2.0)

        forward_lane = road.forward_lanes[1]  # lane_index = 1
        backward_lane = road.backward_lanes[0]  # lane_index = -1

        self.assertEqual(forward_lane.get_one_dimensional_position(reader), 52.0)
        self.assertEqual(backward_lane.get_one_dimensional_position(reader), 48.0)


class TestRoad(unittest.TestCase):
    def test_from_params_creates_lanes_and_uid(self):
        params = RoadParams(
            name="First",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=1,
        )
        road = Road.from_params(params)

        self.assertEqual(road.name, "First")
        self.assertEqual(road.orientation, RoadOrientation.HORIZONTAL)
        self.assertEqual(road.position, 0.0)
        self.assertEqual(road.number_of_forward_lanes, 2)
        self.assertEqual(road.number_of_backward_lanes, 1)
        self.assertEqual(len(road.forward_lanes), 2)
        self.assertEqual(len(road.backward_lanes), 1)
        self.assertTrue(isinstance(road.uid, str))
        self.assertTrue(road.uid)

    def test_update_from_params_updates_lane_counts(self):
        params = RoadParams(
            name="Road",
            orientation=RoadOrientation.HORIZONTAL,
            position=10.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=1,
        )
        road = Road.from_params(params)

        updated = RoadParams(
            name="Road Updated",
            orientation=RoadOrientation.VERTICAL,
            position=20.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=0,
        )
        road.update_from_params(updated)

        self.assertEqual(road.name, "Road Updated")
        self.assertEqual(road.orientation, RoadOrientation.VERTICAL)
        self.assertEqual(road.position, 20.0)
        self.assertEqual(len(road.forward_lanes), 2)
        self.assertEqual(len(road.backward_lanes), 0)
        self.assertEqual(road.number_of_forward_lanes, 2)
        self.assertEqual(road.number_of_backward_lanes, 0)

    def test_validate_raises_for_empty_name(self):
        params = RoadParams(
            name="Valid",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=0,
        )
        road = Road.from_params(params)

        with self.assertRaises(RoadValidationError):
            road.name = ""

    def test_validate_requires_at_least_one_lane(self):
        params = RoadParams(
            name="NoLanes",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=0,
            number_of_backward_lanes=0,
        )
        with self.assertRaises(RoadValidationError):
            Road.from_params(params)

    def test_get_bounds_horizontal(self):
        params = RoadParams(
            name="Bounds",
            orientation=RoadOrientation.HORIZONTAL,
            position=10.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=1,
        )
        road = Road.from_params(params)
        lower, upper = road.get_bounds()

        self.assertLess(lower, upper)

    def test_get_bounds_vertical(self):
        params = RoadParams(
            name="Bounds",
            orientation=RoadOrientation.VERTICAL,
            position=10.0,
            number_of_forward_lanes=2,
            number_of_backward_lanes=1,
        )
        road = Road.from_params(params)
        lower, upper = road.get_bounds()

        self.assertLess(lower, upper)


class TestCarParams(unittest.TestCase):
    def test_get_braking_dist(self):
        params = CarParams(
            name="Car1",
            lane=None,
            color="#ff0000",
            position_on_lane=10.0,
            transition=0.0,
            speed=10.0,
            length=4.0,
            next_turn=None,
            acceleration=0.0,
        )
        dist = params.get_braking_dist(8.0)
        expected = (10.0 * 10.0) / (2.0 * 8.0) + 4.0
        self.assertEqual(dist, expected)


if __name__ == "__main__":
    unittest.main()
