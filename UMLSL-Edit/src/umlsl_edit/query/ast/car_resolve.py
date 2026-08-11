from abc import ABC, abstractmethod

from umlsl_edit.model.entities.car import Car


class CarResolve(ABC):
    """
    An abstraction to resolve a car based on a variable name.
    """
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def resolve(self, variable_car_map: dict[str, Car]) -> Car:
        """
        Resolves the car based on the variable map.
        The variable map maps each variable names its corresponding car.
        """
        pass


class ConstantCarResolve(CarResolve):
    """
    The ConstantCarResolve is used to resolve a constant car specifically referenced to by its name.
    """
    def __init__(self, car: Car):
        super().__init__(car.name)
        self._car = car

    def resolve(self, variable_car_map: dict[str, Car]) -> Car:
        return self._car


class VariableCarResolve(CarResolve):
    """
    The VariableCarResolve is used to resolve a car based on a variable name.
    """
    def __init__(self, car_variable: str):
        super().__init__(car_variable)
        self._car_variable = car_variable

    def resolve(self, variable_car_map: dict[str, Car]) -> Car:
        return variable_car_map[self._car_variable]
