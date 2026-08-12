import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import View, BinaryNode, Precedence, ASTNode

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel

# Safety valves for the critical-point construction. Length constants compose along a chain of
# nested chops, so the number of distinct offsets grows with the chop depth; these bound that growth
# for formulas that nest many chops over many distinct constants. Dropping offsets keeps the search
# sound, and only costs completeness for formulas deeper than the bound.
MAX_CRITICAL_POINTS = 4096
MAX_OFFSET_SUMMANDS = 8


class HorizontalChopNode(BinaryNode):
    """
    The HorizontalChopNode is a binary node that evaluates to true if there exists a horizontal split such that the
    left part evaluates to true and the right part evaluates to true as well.
    """

    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_CHOP, left, right)
        self.latex_left = left.to_latex()
        self.latex_right = right.to_latex()

    @classmethod
    def create_nested_hchop(cls, operands: list[ASTNode]):
        if len(operands) <= 1:
            raise ValueError("At least two operands are required")
        elif len(operands) == 2:
            return cls(operands[0], operands[1])
        else:
            return cls(operands[0], cls.create_nested_hchop(operands[1:]))

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        for split in self.critical_points(view):
            if self.evaluate_at_split(view, traffic_snapshot, variable_car_map, split):
                return True

        return False

    def critical_points(self, view: View) -> list[float]:
        """
        The split positions the horizontal chop has to try.

        The truth of a subformula over an observed space [b, r] can only change when r crosses a
        position at which some atomic proposition changes: the endpoint of a car, of a reservation,
        of a claim, or of a segment. Between two consecutive such positions every atom keeps its
        value, so one representative per open gap suffices, and we use the midpoint. Formulas that
        constrain the length of the observed space add further critical positions, namely the
        constants they compare against, measured from either end of the observed space.

        Returns the base points first (a witness is far more often an endpoint than an interior
        point), then the offsets, then the gap representatives.
        """
        horizon = view.horizon
        b, e = horizon.start, horizon.end

        def within(position: float) -> bool:
            return b < position < e

        base: set[float] = {b, e}

        # endpoints of everything that can make an atom change its truth value
        for occupancy in (view.get_visible_cars(), view.get_reserved_segments(), view.get_claimed_segments()):
            for intervals in occupancy.values():
                for interval in intervals.values():
                    base.update(p for p in (interval.start, interval.end) if within(p))

        # segment borders, which is where `cs` changes
        for virtual_lane in view.virtual_lanes:
            for segment_interval in virtual_lane.segment_intervals:
                interval = segment_interval.interval
                base.update(p for p in (interval.start, interval.end) if within(p))

        offsets: set[float] = set()
        constants = {constant for constant in self.length_constants() if 0.0 < constant < e - b}
        if constants:
            # A chain of n nested chops can compose up to n constants, so the reachable offsets are
            # the sums of constants with repetition, bounded by the chop depth of this subtree.
            #
            # The offsets are measured from the two ends of the observed space only, never from the
            # interior points. A length constraint always constrains the space it is evaluated on,
            # and the recursion evaluates the operands on spaces that begin or end at this split, so
            # an offset from an interior point p is generated again -- as an offset from an end --
            # by the recursive call on the space starting at p. Anchoring at every base point
            # instead multiplies the number of candidates by the size of the view at every level of
            # nesting, which is what made deeply nested length formulas intractable.
            sums: set[float] = {0.0}
            for _ in range(min(self.chop_depth(), MAX_OFFSET_SUMMANDS)):
                grown = {s + c for s in sums for c in constants if s + c <= e - b}
                if grown <= sums or len(grown) > MAX_CRITICAL_POINTS:
                    break
                sums |= grown
            sums.discard(0.0)

            for anchor in (b, e):
                for offset in sums:
                    offsets.update(p for p in (anchor + offset, anchor - offset) if within(p))

        ordered = sorted(base | offsets)
        gap_representatives = [
            (ordered[i] + ordered[i + 1]) / 2.0
            for i in range(len(ordered) - 1)
            if ordered[i + 1] - ordered[i] > 0.0
        ]

        return sorted(base) + sorted(offsets) + gap_representatives

    def chop_depth(self) -> int:
        """
        The largest number of horizontal chops on any path through this subtree, i.e. how many
        length constants can be composed along a chain of nested chops.
        """
        def depth(node: ASTNode) -> int:
            children = [child for child in (getattr(node, "_left", None), getattr(node, "_right", None),
                                            getattr(node, "_child", None)) if child is not None]
            below = max((depth(child) for child in children), default=0)
            return below + 1 if isinstance(node, HorizontalChopNode) else below

        return max(depth(self), 1)

    def evaluate_at_split(self, view: View, traffic_snapshot: "TrafficSnapshotModel", variable_car_map: dict[str, Car],
                          split_value: float):
        horizon = view.horizon

        if not (horizon.start <= split_value <= horizon.end):
            return False

        left_view, right_view = view.chop_horizontally(split_value)

        # if the left part is false, we can skip the computation of the right part
        left_eval = self._left.evaluate(traffic_snapshot, left_view, variable_car_map)
        if left_eval:
            right_eval = self._right.evaluate(traffic_snapshot, right_view, variable_car_map)
            if right_eval:
                # print(
                #   f"hchop: evaluated true on {left_view.horizon} ({self.latex_left}) and {right_view.horizon} ({self.latex_right})")
                return True

        return False

    def _format(self, left: str, right: str) -> str:
        return f"{left} \\frown {right}"


class VerticalChopNode(BinaryNode):
    """
    The VerticalChopNode is a binary node that evaluates to true if there exists a vertical split such that the
    upper part evaluates to true and the lower part evaluates to true as well.
    """

    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_CHOP, left, right)

    @classmethod
    def create_nested_vchop(cls, operands: list[ASTNode]):
        if len(operands) <= 1:
            raise ValueError("At least two operands are required")
        elif len(operands) == 2:
            return cls(operands[0], operands[1])
        else:
            return cls(cls.create_nested_vchop(operands[0:-1]), operands[-1])

    def evaluate(self, traffic_snapshot: "TrafficSnapshotModel", view: View, variable_car_map: dict[str, Car]) -> bool:
        seq_lanes = view.virtual_lanes

        for split_index in range(0, len(seq_lanes) + 1):
            lower_view, upper_view = view.chop_vertically(split_index)
            lower_eval = self._left.evaluate(traffic_snapshot, lower_view, variable_car_map)

            # if the lower part is false, we can skip the computation of the upper part
            if lower_eval:
                right_eval = self._right.evaluate(traffic_snapshot, upper_view, variable_car_map)

                if right_eval:
                    return True

        return False

    def _format(self, left: str, right: str) -> str:
        return f"_{{{right}}}^{{{left}}}"
