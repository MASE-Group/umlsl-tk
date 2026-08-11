import unittest
from unittest.mock import MagicMock, patch

from umlsl_edit.commands.settings.change_braking_acceleration import (
    ChangeBrakingAccelerationCommand,
)
from umlsl_edit.commands.umlsl.add_umlsl_query import AddUMLSLQuery
from umlsl_edit.commands.umlsl.delete_umlsl_query import DeleteUMLSLQuery
from umlsl_edit.commands.umlsl.edit_umlsl_query import EditUMLSLQuery
from umlsl_edit.model.entities.umlsl_query import UMLSLQueryParams
from umlsl_edit.model.errors.settings_errors import SettingsValidationError
from umlsl_edit.model.errors.umlsl_query_errors import UMLSLQueryValidationError


class TestChangeBrakingAccelerationCommand(unittest.TestCase):
    def test_execute_updates_settings(self):
        settings = MagicMock()
        cmd = ChangeBrakingAccelerationCommand(settings, value=3.5)

        cmd.execute()

        settings.set_braking_acceleration.assert_called_once_with(3.5)

    def test_execute_rejects_non_positive(self):
        settings = MagicMock()
        cmd = ChangeBrakingAccelerationCommand(settings, value=0)

        with self.assertRaises(SettingsValidationError):
            cmd.execute()

        settings.set_braking_acceleration.assert_not_called()


class TestAddUMLSLQueryCommand(unittest.TestCase):
    @patch(
        "umlsl_edit.commands.umlsl.add_umlsl_query.UMLSLQuery.from_params",
        autospec=True,
    )
    def test_execute_adds_query_for_existing_car(self, from_params):
        reader = MagicMock()
        model = MagicMock()
        reader.is_car_existing.return_value = True
        params = UMLSLQueryParams(latex="\\phi", assigned_car_uid="car-1", holding=True,
                                  should_only_evaluate_on_cars_lane=True)
        cmd = AddUMLSLQuery(params, model, reader)
        query_instance = MagicMock()
        from_params.return_value = query_instance

        cmd.execute()

        from_params.assert_called_once_with(params)
        model.add_umlsl_query.assert_called_once_with(query_instance)

    def test_execute_rejects_missing_assigned_car(self):
        reader = MagicMock()
        model = MagicMock()
        reader.is_car_existing.return_value = False
        params = UMLSLQueryParams(latex="\\phi", assigned_car_uid="car-1", should_only_evaluate_on_cars_lane=True)

        cmd = AddUMLSLQuery(params, model, reader)

        with self.assertRaises(UMLSLQueryValidationError):
            cmd.execute()

        model.add_umlsl_query.assert_not_called()


class TestEditUMLSLQueryCommand(unittest.TestCase):
    def test_execute_updates_query(self):
        model = MagicMock()
        query = MagicMock()
        model.get_query_by_id.return_value = query
        params = UMLSLQueryParams(latex="\\psi", assigned_car_uid="car-2", should_only_evaluate_on_cars_lane=True)

        cmd = EditUMLSLQuery(query_id="q-1", umlsl_query_params=params, umlsl_queries_model=model)
        cmd.execute()

        model.get_query_by_id.assert_called_once_with("q-1")
        model.update_umlsl_query.assert_called_once_with(query, params)


class TestDeleteUMLSLQueryCommand(unittest.TestCase):
    def test_execute_removes_query(self):
        model = MagicMock()
        model.get_query_by_id.return_value = MagicMock()

        cmd = DeleteUMLSLQuery(query_id="q-1", umlsl_queries_model=model)
        cmd.execute()

        model.get_query_by_id.assert_called_once_with("q-1")
        model.remove_umlsl_query.assert_called_once_with("q-1")


if __name__ == "__main__":
    unittest.main()
