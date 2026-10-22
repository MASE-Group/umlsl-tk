import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast import View, BinaryNode, Precedence, ASTNode

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class _ChopOffsets(typing.NamedTuple):
    left_lengths: frozenset[float]
    right_lengths: frozenset[float]
    operand_anchors: frozenset[float]
    lengths: frozenset[float]
    anchors: frozenset[float]


class HorizontalChopNode(BinaryNode):
    """
    The HorizontalChopNode is a binary node that evaluates to true if there exists a horizontal split such that the
    left part evaluates to true and the right part evaluates to true as well.
    """

    def __init__(self, left: ASTNode, right: ASTNode):
        super().__init__(Precedence.BINARY_CHOP, left, right)
        self.latex_left = left.to_latex()
        self.latex_right = right.to_latex()
        self._offsets: _ChopOffsets | None = None

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

        Whether the left operand holds on [b, r] and the right operand on [r, e] can only change when
        the split r crosses one of these positions:
          - a base point: b, e, or the endpoint of a car, of a reservation, of a claim, or of a
            segment, which is where the atomic propositions change;
          - b plus a length offset of the left operand, or e minus one of the right operand, which
            is where a length comparison changes;
          - a base point plus an anchor offset of either operand, which is where a length
            comparison chained to an atom changes, e.g. a split exactly 1 before a reservation.
        Between two consecutive such positions both operands keep their value, so one representative
        per open gap suffices, and we use the midpoint.

        The offsets are derived from the structure of the operands (see length_offsets and
        anchor_offsets), so every position at which the operands can change is a candidate, however
        deeply the chops are nested, and no bound on the chop depth is needed.

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

        offsets = self._chop_offsets()
        positions: set[float] = set()
        positions.update(p for p in (b + length for length in offsets.left_lengths) if within(p))
        positions.update(p for p in (e - length for length in offsets.right_lengths) if within(p))

        # Anchoring at b and e alone is not enough: in <hchop{l <= 1 and free}{re{c}}> the enclosing
        # chop of the somewhere has to split within 1 before c's reservation, before the chop that
        # reaches the reservation is even evaluated.
        shifts = [shift for shift in offsets.operand_anchors if shift != 0.0 and abs(shift) < e - b]
        for point in base:
            positions.update(p for p in (point + shift for shift in shifts) if within(p))
        positions -= base

        ordered = sorted(base | positions)
        gap_representatives = [
            (ordered[i] + ordered[i + 1]) / 2.0
            for i in range(len(ordered) - 1)
            if ordered[i + 1] - ordered[i] > 0.0
        ]

        return sorted(base) + sorted(positions) + gap_representatives

    def length_offsets(self) -> frozenset[float]:
        return self._chop_offsets().lengths

    def anchor_offsets(self) -> frozenset[float]:
        return self._chop_offsets().anchors

    def _chop_offsets(self) -> _ChopOffsets:
        """
        The offsets of the operands, and those of this chop derived from them.

        The chopped space is as long as both parts together, so its length offsets are the sums of
        one length offset of each operand. A split anchored at a base point p fixes the start of the
        chopped space at p minus a length of the left operand, and its end at p plus a length of the
        right operand, so the anchor offsets of the operands are shifted by those lengths.

        The formula does not change after parsing, but the critical points are computed for every
        observed space the chop is evaluated on, so this is computed once.
        """
        if self._offsets is None:
            left_lengths = self._left.length_offsets()
            right_lengths = self._right.length_offsets()
            operand_anchors = self._left.anchor_offsets() | self._right.anchor_offsets()
            shifts = {-length for length in left_lengths} | right_lengths
            self._offsets = _ChopOffsets(
                left_lengths=left_lengths,
                right_lengths=right_lengths,
                operand_anchors=operand_anchors,
                lengths=frozenset(left + right for left in left_lengths for right in right_lengths),
                anchors=frozenset(anchor + shift for anchor in operand_anchors for shift in shifts),
            )
        return self._offsets

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
