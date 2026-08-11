from umlsl_edit.model.domain_models.traffic_snapshot_reader import TrafficSnapshotReader
from umlsl_edit.model.entities.car import Car
from umlsl_edit.query.ast.ast_parser import ASTParser, ASTParserError, ParsedUMLSLQuery
from umlsl_edit.query.lexer import Lexer, Token


class UMLSLEvaluator:
    """
    The UMLSLEvaluator "acts as an API" to evaluate UMLSL queries.
    """
    def __init__(self, traffic_snapshot: TrafficSnapshotReader):
        self._traffic_snapshot = traffic_snapshot

    def parse_ast(self, query: str, ego: Car) -> ParsedUMLSLQuery:
        """
        Parses a UMLSL query from a string and returns the ParsedUMLSLQuery.
        """
        tokens = Lexer(query).tokenize()
        try:
            return ASTParser(self._traffic_snapshot, ego, tokens).parse_query()
        except ASTParserError as e:
            raise ParserError(e, query, tokens, e.scope_start, e.scope_end)


class ParserError(Exception):
    """
    A ParserError is raised when the ASTParser fails to parse a UMLSL query.
    It converts an ASTParserError into a ParserError since the ASTParserError acts on the token level, whereas the
    ParserError converts the tokens back into information about the input string of the user.

    Attributes:
        input: the input query of the user
        reason: the reason the parser failed
        help: the help message to display to the user
        scope_start: the index *in the input string of the user* where the error starts (inclusive)
        scope_end: the index *in the input string of the user* where the error ends (inclusive)
    """
    def __init__(
            self,
            ast_parser_error: ASTParserError,
            input: str,
            tokens: list[Token],
            scope_1: int,
            scope_2: int,
    ):
        super().__init__(ast_parser_error)
        scope_start = min(scope_1, scope_2)
        scope_end = max(scope_1, scope_2)

        self.input = input
        self.reason = ast_parser_error.reason
        self.help = ast_parser_error.help

        if scope_start >= len(tokens):
            # ASTParser expects new tokens only after the input
            # we indicate this by starting the error after the input
            self.scope_start = len(input) + 1
            self.scope_end = len(input) + 4
        elif scope_end >= len(tokens):
            # ASTParser expects a token after the end of the input, but the starting token is still in bounds
            self.scope_start = tokens[scope_start].start_index
            self.scope_end = len(input) + 3
        else:
            self.scope_start = tokens[scope_start].start_index
            self.scope_end = tokens[scope_end].end_index
