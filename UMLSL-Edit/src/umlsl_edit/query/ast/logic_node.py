import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import View, UnaryNode, BinaryNode, AtomNode, ASTNode, Precedence

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class TrueNode(AtomNode):
    """
    The TrueNode is a unary node that evaluates to true.
    """
    def __init__(self):
        super().__init__("true")

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return True


class NegationNode(UnaryNode):
    """
    The NegationNode is a unary node that negates its child.
    """
    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return not self._child.evaluate(traffic_snapshot, view, variable_car_map)

    def _format(self, child: str) -> str:
        return f"\\neg {child}"


class ConjunctionNode(BinaryNode):
    """
    The ConjunctionNode is a binary node that evaluates to true if both its children evaluate to true.
    """
    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_CONJUNCTION, left, right)

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return (self._left.evaluate(traffic_snapshot, view, variable_car_map)
                and self._right.evaluate(traffic_snapshot, view, variable_car_map))

    def _format(self, left: str, right: str) -> str:
        return f"{left} \\wedge {right}"


class DisjunctionNode(BinaryNode):
    """
    The DisjunctionNode is a binary node that evaluates to true if at least one of its children evaluate to true.
    """
    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_DISJUNCTION, left, right)

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return (self._left.evaluate(traffic_snapshot, view, variable_car_map)
                or self._right.evaluate(traffic_snapshot, view, variable_car_map))

    def _format(self, left: str, right: str) -> str:
        return f"{left} \\vee {right}"


class ImpliesNode(BinaryNode):
    """
    The ImpliesNode is a binary node that evaluates to true if the left child implies the right child. That means,
    the left child evaluates to false or the right child evaluates to true.
    """
    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_DISJUNCTION, left, right)

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        return (not self._left.evaluate(traffic_snapshot, view, variable_car_map)
                or self._right.evaluate(traffic_snapshot, view, variable_car_map))

    def _format(self, left: str, right: str) -> str:
        return f"{left} \\Longrightarrow {right}"
