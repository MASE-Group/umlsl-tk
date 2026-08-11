import unittest
from unittest.mock import MagicMock, patch

from umlsl_edit.commands.cars.add_car import AddCarCommand
from umlsl_edit.commands.cars.delete_car import DeleteCar
from umlsl_edit.commands.cars.edit_car import EditCarCommand
from umlsl_edit.model.entities.car import CarParams
from umlsl_edit.model.errors.car_errors import CarValidationError


class TestAddCarCommand(unittest.TestCase):
    def test_execute_validates_and_adds_car(self):
        reader = MagicMock()
        writer = MagicMock()
        settings = MagicMock()
        car_params = CarParams(
            name="CarA",
            lane=MagicMock(),
            color="#ff00ff",
            position_on_lane=10.0,
            transition=0.0,
            speed=5.0,
            length=4.5,
            next_turn=None,
            acceleration=0.0,
        )

        with patch(
            "umlsl_edit.commands.cars.add_car.Car.from_params",
            autospec=True,
        ) as from_params:
            car_instance = MagicMock()
            from_params.return_value = car_instance

            cmd = AddCarCommand(reader, writer, settings, car_params)
            cmd.execute()

            reader.validate_car_params.assert_called_once_with(car_params, True)
            from_params.assert_called_once_with(car_params, reader, settings)
            writer.add_car.assert_called_once_with(car_instance)


class TestEditCarCommand(unittest.TestCase):
    def test_execute_raises_when_car_missing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_car_existing.return_value = False
        car_params = MagicMock(spec=CarParams)

        cmd = EditCarCommand(reader, writer, car_params, uid="car-1")

        with self.assertRaises(CarValidationError):
            cmd.execute()

        reader.validate_car_params.assert_not_called()
        writer.update_car_with_params.assert_not_called()

    def test_execute_updates_car_when_existing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_car_existing.return_value = True
        car_params = MagicMock(spec=CarParams)

        cmd = EditCarCommand(reader, writer, car_params, uid="car-1")
        cmd.execute()

        reader.validate_car_params.assert_called_once_with(car_params, False, "car-1")
        writer.update_car_with_params.assert_called_once_with("car-1", car_params)


class TestDeleteCarCommand(unittest.TestCase):
    def test_execute_raises_when_car_missing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_car_existing.return_value = False

        cmd = DeleteCar(writer, reader, car_uid="car-1")

        with self.assertRaises(CarValidationError):
            cmd.execute()

        writer.remove_car.assert_not_called()

    def test_execute_removes_when_existing(self):
        reader = MagicMock()
        writer = MagicMock()
        reader.is_car_existing.return_value = True

        cmd = DeleteCar(writer, reader, car_uid="car-1")
        cmd.execute()

        writer.remove_car.assert_called_once_with("car-1")


if __name__ == "__main__":
    unittest.main()
