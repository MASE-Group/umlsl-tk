import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import UnaryNode
from umlsl_edit.query.ast.chop_node import VerticalChopNode, HorizontalChopNode
from umlsl_edit.query.ast.logic_node import TrueNode
from umlsl_edit.query.view import View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class SomewhereNode(UnaryNode):
    """
    A SomewhereNode is a unary node that evaluates to true if the child evaluates to true somewhere in the view. We
    reconstruct it via vertical and horizontal chops.
    """

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        somewhere_node = HorizontalChopNode.create_nested_hchop(
            [
                TrueNode(),
                VerticalChopNode.create_nested_vchop([TrueNode(), self._child, TrueNode()]),
                TrueNode()
            ]
        )
        return somewhere_node.evaluate(traffic_snapshot, view, variable_car_map)

    def to_latex(self) -> str:
        # we do not need to encapsulate anything in parentheses, it is already clear because of <...>
        return self._format(self._child.to_latex())

    def _format(self, child: str) -> str:
        return f"\\langle {child}\\rangle"
