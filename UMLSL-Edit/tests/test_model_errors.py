import unittest

from umlsl_edit.model.errors.car_errors import CarValidationError, CarTrafficSnapshotContextValidationError, CarWarning
from umlsl_edit.model.errors.errors import BaseError, BaseWarning
from umlsl_edit.model.errors.persistence_errors import TrafficSnapshotLoadingError
from umlsl_edit.model.errors.road_errors import RoadValidationError
from umlsl_edit.model.errors.settings_errors import SettingsValidationError
from umlsl_edit.model.errors.umlsl_query_errors import UMLSLQueryValidationError


class TestBaseErrors(unittest.TestCase):

    def test_base_error(self):
        error = BaseError(content="Test content", title="Test Title")
        self.assertEqual(error.content, "Test content")
        self.assertEqual(error.title, "Test Title")
        self.assertEqual(str(error), "Test content")

    def test_base_warning(self):
        warning = BaseWarning(content="Test warning")
        self.assertEqual(warning.content, "Test warning")


class TestCarErrors(unittest.TestCase):

    def test_car_validation_error(self):
        error = CarValidationError(content="Car invalid")
        self.assertEqual(error.content, "Car invalid")
        self.assertEqual(error.title, "Car Validation Error")

    def test_car_traffic_snapshot_context_validation_error(self):
        error = CarTrafficSnapshotContextValidationError(content="Context invalid")
        self.assertEqual(error.content, "Context invalid")
        self.assertEqual(error.title, "Car Validation Error in Traffic Snapshot Context")

    def test_car_warning(self):
        warning = CarWarning(content="Car warning")
        self.assertEqual(warning.content, "Car warning")


class TestPersistenceErrors(unittest.TestCase):

    def test_traffic_snapshot_loading_error(self):
        error = TrafficSnapshotLoadingError(content="Loading failed")
        self.assertEqual(error.content, "Loading failed")
        self.assertEqual(error.title, "Traffic Snapshot Loading Error")


class TestRoadErrors(unittest.TestCase):

    def test_road_validation_error(self):
        error = RoadValidationError(content="Road invalid")
        self.assertEqual(error.content, "Road invalid")
        self.assertEqual(error.title, "Road Validation Error")


class TestSettingsErrors(unittest.TestCase):

    def test_settings_validation_error(self):
        error = SettingsValidationError(message="Settings invalid")
        self.assertEqual(error.content, "Settings invalid")
        self.assertEqual(error.title, "Settings Validation Error")


class TestUMLSLQueryErrors(unittest.TestCase):

    def test_umlsl_query_validation_error(self):
        error = UMLSLQueryValidationError(message="Query invalid")
        self.assertEqual(error.content, "Query invalid")
        self.assertEqual(error.title, "UMLSL Query Validation Error")


if __name__ == "__main__":
    unittest.main()
