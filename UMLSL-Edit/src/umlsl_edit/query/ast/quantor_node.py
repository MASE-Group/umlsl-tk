import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import UnaryNode, ASTNode, View, Precedence

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class ExistsNode(UnaryNode):
    """
    The ExistsNode is a unary node that evaluates to true if the specified variable holds for at least one car.
    Note that we only iterate through the visible cars of ego.
    """
    def __init__(self, variable: str, child: ASTNode):
        super().__init__(child)
        self._variable = variable
        self._precedence = Precedence.UNARY_QUANTOR

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        # the AST parser guarantees that the variable is not already in the map
        for car_uid in view.get_visible_cars().keys():
            new_variable_map = variable_car_map.copy()
            new_variable_map[self._variable] = traffic_snapshot.cars[car_uid]

            if self._child.evaluate(traffic_snapshot, view, new_variable_map):
                return True

        return False

    def _format(self, child: str) -> str:
        return f"\\exists {self._variable}: {child}"


class ForallNode(UnaryNode):
    """
    The ForallNode is a unary node that evaluates to true if the specified variable holds for all cars.
    Note that we only iterate through the visible cars of ego.
    """
    def __init__(self, variable: str, child: ASTNode):
        super().__init__(child)
        self._variable = variable
        self._precedence = Precedence.UNARY_QUANTOR

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        # the AST parser guarantees that the variable is not already in the map
        for car_uid in view.get_visible_cars().keys():
            new_variable_map = variable_car_map.copy()
            new_variable_map[self._variable] = traffic_snapshot.cars[car_uid]

            if not self._child.evaluate(traffic_snapshot, view, new_variable_map):
                return False

        return True

    def _format(self, child: str) -> str:
        return f"\\forall {self._variable}: {child}"
