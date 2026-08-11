import typing

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.environment.view_coordinate_translation import translate_into_ego_coordinates
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.segments.virtual_lane import VirtualLane
from umlsl_edit.query.ast.ast import ASTNode
from umlsl_edit.query.ast.car_resolve import ConstantCarResolve, VariableCarResolve, CarResolve
from umlsl_edit.query.ast.chop_node import HorizontalChopNode, VerticalChopNode
from umlsl_edit.query.ast.claim_node import ClaimNode
from umlsl_edit.query.ast.crossing_node import CrossingSegmentNode
from umlsl_edit.query.ast.equality_node import CarEqualityNode, CarNotEqualsNode
from umlsl_edit.query.ast.free_node import FreeNode
from umlsl_edit.query.ast.horizon_cmp_node import HorizonCmpGreaterNode, HorizonCmpGreaterEqualsNode, \
    HorizonCmpLessNode, HorizonCmpLessEqualsNode
from umlsl_edit.query.ast.logic_node import ConjunctionNode, DisjunctionNode, NegationNode, TrueNode, \
    ImpliesNode
from umlsl_edit.query.ast.quantor_node import ExistsNode, ForallNode
from umlsl_edit.query.ast.reserve_node import ReserveNode
from umlsl_edit.query.ast.somewhere_node import SomewhereNode
from umlsl_edit.query.lexer import Token, TokenType
from umlsl_edit.query.view import View

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class ParsedUMLSLQuery:
    """
    A ParsedUMLSLQuery is a query that has been parsed into an AST. It holds the list of cars being referenced in the
    query and the latex code of the query.
    Additionally, a ParsedUMLSLQuery can be evaluated.

    Attributes:
        car_references: the list of cars that are referenced in the query
        latex_code: the latex code of the query
    """
    def __init__(self, traffic_snapshot: "TrafficSnapshotModel", ego: Car, ast: ASTNode, car_references: list[Car]):
        self._traffic_snapshot = traffic_snapshot
        self._ast = ast
        self._ego = ego
        self.car_references = car_references
        self.latex_code = ast.to_latex()

    def evaluate(self, evaluate_ego_lane_only: bool) -> bool:
        """
        Evaluates the query. If evaluate_ego_lane_only is True, the query is evaluated only in the ego lane. Otherwise,
        on the full view of ego.
        """
        if evaluate_ego_lane_only:
            return self._evaluate_on_ego_lane()
        else:
            return self._evaluate_in_view()

    def _evaluate_on_ego_lane(self) -> bool:
        return self._evaluate_parallel_virtual_lane([self._ego.environment.path_virtual_lane])

    def _evaluate_in_view(self) -> bool:
        for parallel_virtual_lane in self._ego.environment.parallel_virtual_lanes:
            if self._evaluate_parallel_virtual_lane(parallel_virtual_lane):
                return True

        return False

    def _evaluate_parallel_virtual_lane(self, parallel_virtual_lane: list[VirtualLane]) -> bool:
        horizon = self._ego.environment.horizon

        # collect visible segments
        segments_in_view: list[Segment] = []
        for virtual_lane in parallel_virtual_lane:
            for segment_interval in virtual_lane.segment_intervals:
                if segment_interval.interval.intersects(horizon):
                    segments_in_view.append(segment_interval.segment)

        # translate environment information into ego's coordinate system
        coordinate_translation = translate_into_ego_coordinates(
            self._traffic_snapshot, self._ego, horizon, parallel_virtual_lane
        )

        view = View(
            parallel_virtual_lane,
            segments_in_view,
            horizon,
            self._ego,
            coordinate_translation.visible,
            coordinate_translation.reserved,
            coordinate_translation.claimed,
        )

        return self._ast.evaluate(self._traffic_snapshot, view, {})


class ASTParser:
    """
    The ASTParser parses a query into an AST. The AST is a recursive-descent parser that builds an abstract syntax tree.
    """
    def __init__(self, ts: "TrafficSnapshotModel", ego: Car, tokens: list[Token]):
        self._ts = ts
        self._tokens = tokens
        self._cars = ts.get_car_list()
        self._ego = ego
        self._car_references: list[Car] = [ego]

    def parse_query(self) -> ParsedUMLSLQuery:
        """
        Parses the query into an AST and returns a ParsedUMLSLQuery.
        """
        ast = self.parse_ast()
        return ParsedUMLSLQuery(self._ts, self._ego, ast, self._car_references)

    def parse_ast(self) -> ASTNode:
        if not self._tokens:
            raise SyntaxError("Empty token list")
        return self.parse_ast_rec(0, len(self._tokens) - 1, [])

    def parse_ast_rec(self, start: int, end: int, declared_variables: list[str]) -> ASTNode:
        if start > end:
            raise ASTParserError(
                "expected expression here",
                min(start, end + 1),
                start
            )

        tokens = self._tokens

        height = 0
        split_index = -1
        # we need a value that is bigger than all others, in python there is no "max_int"
        min_precedence = float('inf')

        i: int = start
        while i <= end:
            token = tokens[i]

            if token.type in {TokenType.L_PAREN, TokenType.L_CURLY, TokenType.LESS_THAN}:
                height += 1
            elif token.type in {TokenType.R_PAREN, TokenType.R_CURLY, TokenType.GREATER_THAN}:
                height -= 1
            elif height == 0 and token.type.is_infix_binary_op:
                precedence = token.type.get_infix_binary_op_precedence()
                # Find the operator with the lowest binding (left-associativity)
                if precedence <= min_precedence:
                    min_precedence = precedence
                    split_index = i
            i += 1

        if height != 0:
            raise ASTParserError(
                "unbalanced parentheses",
                start,
                end,
                "Consider adding/removing '(', ')', '<' or '{', '}', '>'"
            )

        if split_index != -1:
            return self.parse_infix(start, end, split_index, declared_variables)

        if tokens[start].type == TokenType.L_PAREN and tokens[end].type == TokenType.R_PAREN:
            return self.parse_ast_rec(start + 1, end - 1, declared_variables)

        if tokens[start].type == TokenType.LESS_THAN and tokens[end].type == TokenType.GREATER_THAN:
            return SomewhereNode(self.parse_ast_rec(start + 1, end - 1, declared_variables))

        return self.parse_prefix(start, end, declared_variables)

    def parse_infix(self, start: int, end: int, split_index: int, declared_variables: list[str]) -> ASTNode:
        token = self._tokens[split_index]
        token_type = token.type

        if not (start < split_index < end <= len(self._tokens) - 1):
            if not start < split_index:
                raise ASTParserError(
                    "missing first argument",
                    start,
                    split_index,
                    f"Consider adding an argument before '{token_type.value}'"
                )
            else:
                scope_end = len(self._tokens) if end == len(self._tokens) - 1 else end
                raise ASTParserError(
                    "missing second argument",
                    split_index,
                    scope_end,
                    f"Consider adding an argument after '{token_type.value}'"
                )

        if token_type in {TokenType.EQUALS, TokenType.NOT_EQUALS}:
            car1 = self.parse_car(start, declared_variables)
            car2 = self.parse_car(end, declared_variables)
            match token_type:
                case TokenType.EQUALS:
                    return CarEqualityNode(car1, car2)
                case TokenType.NOT_EQUALS:
                    return CarNotEqualsNode(car1, car2)
        else:
            left_ast = self.parse_ast_rec(start, split_index - 1, declared_variables)
            right_ast = self.parse_ast_rec(split_index + 1, end, declared_variables)
            match token_type:
                case TokenType.AND:
                    return ConjunctionNode(left_ast, right_ast)
                case TokenType.OR:
                    return DisjunctionNode(left_ast, right_ast)
                case TokenType.IMPLIES:
                    return ImpliesNode(left_ast, right_ast)
                case _:
                    raise NotImplementedError(f"Unknown binary operator {token_type}")

    def parse_prefix(self, start: int, end: int, declared_variables: list[str]) -> ASTNode:
        token = self._tokens[start]
        token_type = token.type

        if token_type.is_atom_op:
            return self.parse_atom_node(token_type, start, end)
        elif token_type.is_unary_op:
            return self.parse_unary_node(token_type, start, end, declared_variables)
        elif token_type.is_unary_cmp_op:
            return self.parse_unary_cmp_node(token_type, start, end)
        elif token_type.is_binary_op:
            return self.parse_binary_node(start, end, declared_variables)
        else:
            raise ASTParserError(
                f"unknown token '{token}'",
                start,
                end,
                "Consider using an operator from the help page below"
            )

    def parse_atom_node(self, token_type: TokenType, start: int, end: int) -> ASTNode:
        if start != end:
            raise ASTParserError(
                "expected no arguments",
                start + 1,
                end,
                f"Consider removing the arguments after '{token_type.value}'"
            )
        match token_type:
            case TokenType.TRUE:
                return TrueNode()
            case TokenType.FREE:
                return FreeNode()
            case TokenType.CROSSING:
                return CrossingSegmentNode()
            case _:
                raise NotImplementedError(f"Unknown atom operator {token_type}")

    def parse_unary_cmp_node(self, token_type: TokenType, start: int, end: int) -> ASTNode:
        help_correct_definition = "Consider defining the operator like 'l cmp number', where cmp is one of [<, <=, >, >=]"
        if start == end:
            raise ASTParserError(
                "expected exactly one argument",
                start,
                end,
                help_correct_definition
            )

        number_literal = self._tokens[start + 1]
        literal_value = number_literal.value()
        length: float | None

        try:
            length = float(literal_value)
        except (ValueError, TypeError):
            length = None

        if number_literal.type != TokenType.LITERAL or length is None:
            raise ASTParserError(
                "expected number literal",
                start + 1,
                start + 1,
                help_correct_definition
            )

        match token_type:
            case TokenType.HORIZON_GT:
                return HorizonCmpGreaterNode(length)
            case TokenType.HORIZON_GE:
                return HorizonCmpGreaterEqualsNode(length)
            case TokenType.HORIZON_LT:
                return HorizonCmpLessNode(length)
            case TokenType.HORIZON_LE:
                return HorizonCmpLessEqualsNode(length)
            case _:
                raise NotImplementedError(f"Unknown unary compare operator {token_type}")

    def parse_unary_node(self, token_type: TokenType, start: int, end: int, declared_variables: list[str]) -> ASTNode:
        if start == end:
            raise ASTParserError(
                "expected exactly one argument",
                start,
                end,
                f"Consider defining the operator like '{token_type.value}{{arg}}'"
            )

        if token_type in {TokenType.NEGATION, TokenType.NEGATION_SHORT}:
            return NegationNode(self.parse_ast_rec(start + 1, end, declared_variables))
        else:
            match token_type:
                case TokenType.CLAIM:
                    return ClaimNode(self.parse_car_argument(token_type, start + 1, end, declared_variables))
                case TokenType.RESERVE:
                    return ReserveNode(self.parse_car_argument(token_type, start + 1, end, declared_variables))
                case _:
                    raise NotImplementedError(f"Unknown unary operator {token_type}")

    def parse_binary_node(self, start: int, end: int, declared_variables: list[str]) -> ASTNode:
        token = self._tokens[start]
        token_type = token.type

        if token_type.is_quantor_op:
            help_message = f"Consider defining {token_type.value} like '{token_type.value} c: ...'"
            literal = None if start >= end else self._tokens[start + 1]
            if literal is None or literal.type != TokenType.LITERAL:
                raise ASTParserError(
                    "expected variable name",
                    start,
                    start + 1,
                    help_message
                )
            variable = literal.value()
            self.validate_variable_name(variable, start, declared_variables)
            colon = None if start >= end - 1 else self._tokens[start + 2]
            if colon is None or colon.type != TokenType.COLON:
                raise ASTParserError(
                    "expected ':' after variable",
                    min(start + 2, end),
                    max(start + 2, end),
                    help_message
                )
            new_declared_variables = declared_variables.copy()
            new_declared_variables.append(variable)
            match token_type:
                case TokenType.EXISTS:
                    return ExistsNode(variable, self.parse_ast_rec(start + 3, end, new_declared_variables))
                case TokenType.FORALL:
                    return ForallNode(variable, self.parse_ast_rec(start + 3, end, new_declared_variables))
                case _:
                    raise NotImplementedError(f"Unknown quantor operator {token_type}")
        else:
            operands: list[ASTNode] = []

            arg_start = start + 1
            while arg_start < end:
                arg_end = self.find_closing_argument_index(arg_start, end)
                operands.append(self.parse_expression_argument(arg_start, arg_end, declared_variables))
                arg_start = arg_end + 1

            if len(operands) <= 1:
                help_message = f"Consider defining the operator like '{token_type.value}{{arg1}}{{arg2}}...'"
                raise ASTParserError(
                    "expected at least two arguments",
                    start + 1,
                    end,
                    help_message
                )

            match token_type:
                case TokenType.H_CHOP:
                    return HorizontalChopNode.create_nested_hchop(operands)
                case TokenType.V_CHOP:
                    return VerticalChopNode.create_nested_vchop(operands)
                case _:
                    raise NotImplementedError(f"Unknown binary operator {token_type}")

    def validate_variable_name(self, variable: str, start: int, declared_variables: list[str]):
        reason: None | str = None

        if variable in map(lambda car: car.name, self._cars):
            reason = f"'{variable}' is a car name"
        elif variable in declared_variables:
            reason = f"'{variable}' is already defined in scope"
        elif variable.__contains__("\\"):
            # we prevent \ because that is used in LaTeX, otherwise the user could define LaTeX symbols that way
            reason = "variable cannot contain '\\'"

        if reason is not None:
            raise ASTParserError(
                reason,
                start + 1,
                start + 1,
                "Consider using a different variable name"
            )

    def find_closing_argument_index(self, start_index: int, end_index: int) -> int:
        if start_index >= end_index:
            raise ASTParserError(
                "expected arguments here",
                min(start_index, end_index + 1),
                start_index,
                "Consider adding an argument like '{arg}'"
            )

        return self.find_closing_index(start_index, end_index, TokenType.L_CURLY, TokenType.R_CURLY)

    def find_closing_index(
            self,
            start_index: int,
            end_index: int,
            open_type: TokenType,
            close_type: TokenType
    ) -> int:
        parentheses_depth = 0
        for i in range(start_index, end_index + 1):
            token = self._tokens[i]
            if token.type == open_type:
                parentheses_depth += 1
            elif token.type == close_type:
                parentheses_depth -= 1
                if parentheses_depth == 0:
                    return i
        raise ASTParserError(
            f"unbalanced '{open_type.value}' and '{close_type.value}'",
            start_index,
            end_index,
            f"Consider adding/removing '{open_type.value}' or '{close_type.value}'"
        )

    def parse_expression_argument(self, start: int, end: int, declared_variables: list[str]) -> ASTNode:
        if self._tokens[start].type != TokenType.L_CURLY:
            raise ASTParserError(
                "argument must start by '{'",
                start,
                end
            )

        if self._tokens[end].type != TokenType.R_CURLY:
            raise ASTParserError(
                "argument must end in '}'",
                start,
                end
            )

        return self.parse_ast_rec(start + 1, end - 1, declared_variables)

    def parse_car_argument(self, token_type: TokenType, start: int, end: int,
                           declared_variables: list[str]) -> CarResolve:
        if self._tokens[start].type != TokenType.L_CURLY:
            raise ASTParserError(
                "argument must start by '}'",
                start,
                end
            )

        if self._tokens[end].type != TokenType.R_CURLY:
            raise ASTParserError(
                "argument must end in '}'",
                start,
                end
            )

        if start + 1 != end - 1:
            raise ASTParserError(
                "expected exactly one literal token",
                start,
                end,
                f"Consider defining the operator like '{token_type.value}{{name}}'"
            )

        return self.parse_car(start + 1, declared_variables)

    def parse_car(self, index: int, declared_variables: list[str]):
        token = self._tokens[index]
        value = token.value()
        if value is None:
            raise ASTParserError(
                "expected literal token",
                index,
                index,
                "Use letters to refer to cars or variables"
            )

        # check if value is a car
        for car in self._cars:
            if car.name == value:
                self._car_references.append(car)
                return ConstantCarResolve(car)

        # value is not a car, try to resolve it as a variable
        if value in declared_variables:
            return VariableCarResolve(value)

        available_cars = list(map(lambda car: car.name, self._cars))
        available_variables = declared_variables

        help_msg = f"Consider referring to one of {available_cars} (cars)"
        if len(available_variables) > 0:
            help_msg += f" or {available_variables} (vars)"

        raise ASTParserError(
            f"'{value}' neither refers to a car nor a variable",
            index,
            index,
            help_msg
        )


class ASTParserError(Exception):
    """
    An ASTParserError is raised if the ASTParser fails to parse the list of tokens.

    Attributes:
        reason: the reason why the parser failed
        help: the help message to display to the user
        scope_start: the index of *the first token* where the error starts (inclusive)
        scope_end: the index of *the last token* where the error starts (inclusive)
    """
    def __init__(self, reason: str, scope_start: int, scope_end: int, help: str | None = None):
        super().__init__(reason)
        self.reason = reason
        self.help = help
        self.scope_start = scope_start
        self.scope_end = scope_end
