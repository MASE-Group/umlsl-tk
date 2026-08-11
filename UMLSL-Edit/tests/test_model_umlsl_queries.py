import json
import unittest
from unittest.mock import Mock

from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery, UMLSLQueryParams
from umlsl_edit.model.errors.umlsl_query_errors import UMLSLQueryValidationError


class TestUMLSLQueriesModel(unittest.TestCase):
    def setUp(self):
        settings = SettingsModel(braking_acceleration=2.0, max_speed=10.0)
        self.ts_model = TrafficSnapshotModel(settings_model=settings)
        self.ts_model.is_car_existing = Mock(return_value=True)

    def test_add_get_update_remove_query(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        params = UMLSLQueryParams(latex="\\phi", assigned_car_uid="car-1", should_only_evaluate_on_cars_lane=True)
        query = UMLSLQuery.from_params(params)

        model.add_umlsl_query(query)
        fetched = model.get_query_by_id(query.uid)
        self.assertEqual(fetched.uid, query.uid)
        self.assertEqual(fetched.latex, "\\phi")

        updated_params = UMLSLQueryParams(latex="\\psi", assigned_car_uid="car-2",
                                          should_only_evaluate_on_cars_lane=True, holding=True)
        model.update_umlsl_query(fetched, updated_params)

        updated = model.get_query_by_id(query.uid)
        self.assertEqual(updated.latex, "\\psi")
        self.assertEqual(updated.assigned_car_uid, "car-2")
        self.assertTrue(updated.holding)

        model.remove_umlsl_query(query.uid)
        with self.assertRaises(UMLSLQueryValidationError):
            model.get_query_by_id(query.uid)

    def test_get_query_by_id_raises(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        with self.assertRaises(UMLSLQueryValidationError):
            model.get_query_by_id("missing")

    def test_to_dict_serializes(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        query = UMLSLQuery.from_params(
            UMLSLQueryParams(latex="q", assigned_car_uid="car-1", should_only_evaluate_on_cars_lane=True))
        model.add_umlsl_query(query)

        payload = model.to_dict()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["uid"], query.uid)
        self.assertEqual(payload[0]["latex"], "q")
        self.assertEqual(payload[0]["assigned_car_uid"], "car-1")

    def test_clear_removes_all(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        q1 = UMLSLQuery.from_params(
            UMLSLQueryParams(latex="q1", assigned_car_uid="car-1", should_only_evaluate_on_cars_lane=True))
        q2 = UMLSLQuery.from_params(
            UMLSLQueryParams(latex="q2", assigned_car_uid="car-2", should_only_evaluate_on_cars_lane=True))
        model.add_umlsl_query(q1)
        model.add_umlsl_query(q2)

        model.clear()
        self.assertEqual(model.get_queries(), {})

    def test_from_dict_loads_queries_and_preserves_uid(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        payload = [
            {"uid": "q-1", "latex": "x", "assigned_car_uid": "car-1", "should_only_evaluate_on_cars_lane": True},
            {"uid": "q-2", "latex": "y", "assigned_car_uid": "car-2", "should_only_evaluate_on_cars_lane": False},
        ]

        model.from_dict(payload)
        self.assertEqual(model.get_query_by_id("q-1").latex, "x")
        self.assertEqual(model.get_query_by_id("q-2").assigned_car_uid, "car-2")

    def test_from_dict_validates_payload(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)

        with self.assertRaises(ValueError):
            model.from_dict("not-a-list")

        with self.assertRaises(ValueError):
            model.from_dict([1, 2])

    def test_from_json_loads(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        data = [
            {"uid": "q-1", "latex": "x", "assigned_car_uid": "car-1", "should_only_evaluate_on_cars_lane": True},
        ]
        model.from_json(json.dumps(data))

        self.assertEqual(model.get_query_by_id("q-1").latex, "x")

    def test_to_json_round_trip(self):
        model = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        query = UMLSLQuery.from_params(UMLSLQueryParams(latex="q", assigned_car_uid="car-1", should_only_evaluate_on_cars_lane=True))
        model.add_umlsl_query(query)

        json_payload = model.to_json()
        reloaded = UMLSLQueriesModel(traffic_snapshot=self.ts_model)
        reloaded.from_json(json_payload)

        fetched = reloaded.get_query_by_id(query.uid)
        self.assertEqual(fetched.latex, "q")
        self.assertEqual(fetched.assigned_car_uid, "car-1")


if __name__ == "__main__":
    unittest.main()
