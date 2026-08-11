import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import AtomNode, Precedence
from umlsl_edit.query.ast.car_resolve import CarResolve
from umlsl_edit.query.view import View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class CarEqualityNode(AtomNode):
    """
    The CarEqualityNode is a unary node that evaluates to true if the specified cars are equal (in the sense of being
    the same object).
    """
    def __init__(self, car_resolve1: CarResolve, car_resolve2: CarResolve):
        super().__init__(f"{car_resolve1.name} = {car_resolve2.name}")
        self._car_resolve1 = car_resolve1
        self._car_resolve2 = car_resolve2
        self._precedence = Precedence.UNARY_EQUALITY

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return self._car_resolve1.resolve(variable_car_map) is self._car_resolve2.resolve(variable_car_map)


class CarNotEqualsNode(AtomNode):
    """
    The CarNotEqualsNode is a unary node that evaluates to true if the specified cars are not equal (in the sense of
    being the same object).
    """
    def __init__(self, car_resolve1: CarResolve, car_resolve2: CarResolve):
        super().__init__(f"{car_resolve1.name} \\neq {car_resolve2.name}")
        self._car_resolve1 = car_resolve1
        self._car_resolve2 = car_resolve2
        self._precedence = Precedence.UNARY_EQUALITY

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return not (self._car_resolve1.resolve(variable_car_map) is self._car_resolve2.resolve(variable_car_map))
