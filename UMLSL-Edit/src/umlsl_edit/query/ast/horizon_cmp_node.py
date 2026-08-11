import typing
from typing import Callable

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import AtomNode
from umlsl_edit.query.view import View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class HorizonComparisonNode(AtomNode):
    """
    The HorizonComparisonNode is a unary node that evaluates to true if the horizon length satisfies the specified
    comparison.
    """
    def __init__(self, latex_symbol: str, cmp: Callable[[float, float], bool], length: float):
        super().__init__(f"\\ell {latex_symbol} {length}")
        self._length = length
        self._cmp = cmp

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return self._cmp(view.horizon.length(), self._length)


class HorizonCmpGreaterEqualsNode(HorizonComparisonNode):
    """
    The HorizonCmpGreaterEqualsNode is a unary node that evaluates to true if the horizon length is greater than or
    equal to the specified length.
    """
    def __init__(self, length: float):
        super().__init__("\\geq", lambda x, y: x >= y, length)


class HorizonCmpGreaterNode(HorizonComparisonNode):
    """
    The HorizonCmpGreaterNode is a unary node that evaluates to true if the horizon length is greater than the specified
    length.
    """
    def __init__(self, length: float):
        super().__init__(">", lambda x, y: x > y, length)


class HorizonCmpLessNode(HorizonComparisonNode):
    """
    The HorizonCmpLessNode is a unary node that evaluates to true if the horizon length is less than the specified length.
    """
    def __init__(self, length: float):
        super().__init__("<", lambda x, y: x < y, length)


class HorizonCmpLessEqualsNode(HorizonComparisonNode):
    """
    The HorizonCmpLessEqualsNode is a unary node that evaluates to true if the horizon length is less than or equal to
    the specified length.
    """
    def __init__(self, length: float):
        super().__init__("\\leq", lambda x, y: x <= y, length)
