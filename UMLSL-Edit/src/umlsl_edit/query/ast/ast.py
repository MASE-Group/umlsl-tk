import typing
from abc import abstractmethod, ABC
from enum import IntEnum

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.view import View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class Precedence(IntEnum):
    """
    Assigns a value to each AST Node.
    Higher value = binds tighter (evaluated first).
    """
    ATOM = 50  # Nullary Nodes
    UNARY = 40
    UNARY_EQUALITY = 35
    BINARY_CHOP = 30  # Horizontal Chop, Vertical Chop
    BINARY_CONJUNCTION = 20  # And
    BINARY_DISJUNCTION = 10  # Or
    UNARY_QUANTOR = 0


class ASTNode(ABC):
    """
    The ASTNode represents a node in the abstract syntax tree (AST) and holds the precedence (see above).
    """
    def __init__(self, precedence: Precedence):
        self._precedence = precedence

    @abstractmethod
    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        """
        Evaluates the ASTNode.

        Args:
            traffic_snapshot: the traffic snapshot to evaluate the ASTNode on
            view: the view to evaluate the ASTNode on
            variable_car_map: a map of variable names to Car objects (initially empty, only set by quantor nodes)
        """
        pass

    @abstractmethod
    def to_latex(self) -> str:
        """
        Converts the ASTNode to a (real) LaTeX string.
        """
        pass

    def length_offsets(self) -> frozenset[float]:
        """
        The lengths of the observed space at which this subtree can change its truth value; always
        contains 0.

        These are needed as critical points by the horizontal chop: a formula such as
        "l >= 2 and l <= 2" is only satisfied by the single split at distance 2 from the start of the
        observed space, which is in general not the endpoint of any car, reservation or claim. A
        horizontal chop adds up the lengths of its operands, so they are composed bottom-up.
        """
        return frozenset({0.0})

    def anchor_offsets(self) -> frozenset[float]:
        """
        The offsets from the base points (the endpoints of cars, reservations, claims and segments)
        at which an end of the observed space can change the truth value of this subtree.

        A subtree that depends on where the observed space lies changes at the base points
        themselves (offset 0). A horizontal chop shifts these by the lengths of its operands: in
        "hchop{(l >= 1 and l <= 1) and free}{re{c}}" the observed space has to start exactly 1
        before c's reservation. Empty if the subtree does not depend on where the observed space
        lies; atoms default to depending on it, which only costs candidates, never witnesses.
        """
        return frozenset({0.0})


class AtomNode(ASTNode, ABC):
    """
    The AtomNode represents a leaf node in the AST.
    """
    def __init__(self, latex_code):
        super().__init__(Precedence.ATOM)
        self._latex_code = latex_code
        pass

    def to_latex(self) -> str:
        return self._latex_code


class UnaryNode(ASTNode, ABC):
    """
    The UnaryNode represents a unary node in the AST.
    """
    def __init__(self, child: ASTNode):
        super().__init__(Precedence.UNARY)
        self._child = child

    def length_offsets(self) -> frozenset[float]:
        return self._child.length_offsets()

    def anchor_offsets(self) -> frozenset[float]:
        return self._child.anchor_offsets()

    def to_latex(self) -> str:
        child_text = self._child.to_latex()

        # For example, NOT (A AND B) -> NOT has precedence over AND -> add parentheses
        if self._precedence > self._child._precedence:
            child_text = f"\\left({child_text}\\right)"

        return self._format(child_text)

    @abstractmethod
    def _format(self, child: str) -> str:
        pass


class BinaryNode(ASTNode, ABC):
    """
    The BinaryNode represents a binary node in the AST.
    """
    def __init__(self, precedence: Precedence, left: ASTNode, right: ASTNode):
        super().__init__(precedence)
        self._left = left
        self._right = right

    def length_offsets(self) -> frozenset[float]:
        return self._left.length_offsets() | self._right.length_offsets()

    def anchor_offsets(self) -> frozenset[float]:
        return self._left.anchor_offsets() | self._right.anchor_offsets()

    def to_latex(self) -> str:
        left_text = self._left.to_latex()
        right_text = self._right.to_latex()

        if self._precedence > self._left._precedence:
            left_text = f"\\left({left_text}\\right)"

        if self._precedence > self._right._precedence:
            right_text = f"\\left({right_text}\\right)"

        return self._format(left_text, right_text)

    @abstractmethod
    def _format(self, left: str, right: str) -> str:
        pass
