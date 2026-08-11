import re
from abc import ABC, abstractmethod
from enum import Enum


class TokenType(Enum):
    """
    Defines all the tokens that are used to parse a UMLSL query. Each token is defined by a regular expression pattern.
    Note that the definition order matters. For example, the token "=>" defined before ">" tells the Lexer to parse
    "=>" first and then consider ">".
    """
    L_PAREN = "\\("
    R_PAREN = "\\)"
    L_CURLY = "\\{"
    R_CURLY = "\\}"
    COLON = ":"
    HORIZON_GE = "l\\s*>="
    HORIZON_LE = "l\\s*<="
    HORIZON_LT = "l\\s*<"
    HORIZON_GT = "l\\s*>"
    IMPLIES = "=>"
    LESS_THAN = "<"
    GREATER_THAN = ">"
    H_CHOP = "hchop"
    V_CHOP = "vchop"
    CLAIM = "cl"
    CROSSING = "cs"
    RESERVE = "re"
    NOT_EQUALS = "!="
    EQUALS = "="
    FREE = "free"
    AND = "and"
    OR = "or"
    NEGATION = "neg"
    NEGATION_SHORT = "!"
    EXISTS = "exists"
    FORALL = "forall"
    TRUE = "true"
    LITERAL = "LITERAL"  # value "LITERAL" is a placeholder

    @property
    def is_infix_binary_op(self):
        return self in _INFIX_BINARY_OPS

    @property
    def is_prefix_binary_op(self):
        return self in _PREFIX_BINARY_OPS

    @property
    def is_binary_op(self):
        return self.is_infix_binary_op or self.is_prefix_binary_op

    @property
    def is_unary_cmp_op(self):
        return self in _UNARY_CMP_OPS

    @property
    def is_unary_op(self):
        return self in _UNARY_OPS

    @property
    def is_atom_op(self):
        return self in _ATOM_OPS

    @property
    def is_quantor_op(self):
        return self in _QUANTOR_OPS

    def get_infix_binary_op_precedence(self):
        if not self.is_infix_binary_op:
            raise ValueError(f"Token {self} is not an infix binary operation.")
        return _INFIX_BINARY_OPS_PRECEDENCE[self]


_ATOM_OPS = {
    TokenType.TRUE,
    TokenType.FREE,
    TokenType.CROSSING
}
_UNARY_OPS = {
    TokenType.NEGATION,
    TokenType.NEGATION_SHORT,
    TokenType.CLAIM,
    TokenType.RESERVE,
}
_UNARY_CMP_OPS = {
    TokenType.HORIZON_GT,
    TokenType.HORIZON_GE,
    TokenType.HORIZON_LT,
    TokenType.HORIZON_LE,
}

### For tokens that correspond to operations and require 2 parameters, we specify whether they are infix ({p1} op {p2}) or
### prefix (op {p1}{p2})
_INFIX_BINARY_OPS = {
    TokenType.AND,
    TokenType.OR,
    TokenType.IMPLIES,
    TokenType.EQUALS,
    TokenType.NOT_EQUALS,
}
_PREFIX_BINARY_OPS = {
    TokenType.H_CHOP,
    TokenType.V_CHOP,
    TokenType.EXISTS,
    TokenType.FORALL
}
_QUANTOR_OPS = {
    TokenType.EXISTS,
    TokenType.FORALL
}
_INFIX_BINARY_OPS_PRECEDENCE = {
    TokenType.AND: 2,
    TokenType.OR: 1,
    TokenType.IMPLIES: 0,
    TokenType.EQUALS: 4,  # irrelevant since equality requires parameters to be cars (unambiguous since no expressions are involved)
    TokenType.NOT_EQUALS: 4, # irrelevant since equality requires parameters to be cars (unambiguous since no expressions are involved)
}


class Token(ABC):
    """
    This class represents a token in the UMLSL query and holds information about the starting index and end index
    in the input string of the user.
    """
    def __init__(self, type: TokenType, start_index: int, end_index: int):
        self.type = type
        self.start_index = start_index
        self.end_index = end_index

    @abstractmethod
    def value(self) -> str | None:
        """
        Returns the value of the token.
        For SimpleTokens, this is always None; Literals return their literal value.
        """
        pass


class SimpleToken(Token):
    """
    A SimpleToken represents a token that does not have a literal value.
    """
    def value(self) -> None:
        return None

    def __str__(self):
        return f"{self.type.name}"


class Literal(Token):
    """
    A Literal represents a token that has a literal value.
    """
    def __init__(self, literal_value: str, start_index: int, end_index: int):
        super().__init__(TokenType.LITERAL, start_index, end_index)
        self._literal_value = literal_value

    def value(self) -> str:
        """
        Returns the value of this literal.
        """
        return self._literal_value

    def __str__(self):
        return f"{self.type.name}('{self._literal_value}')"


class Lexer:
    def __init__(self, text: str):
        self._input = text

    def tokenize(self) -> list[Token]:
        """
        Splits the input string into a list of tokens.
        """
        query_input = self._input

        token_patterns = []
        for t in TokenType:
            if t is not TokenType.LITERAL:
                pattern = f"(?P<{t.name}>{t.value})"
                token_patterns.append(pattern)

        master_pattern = re.compile("|".join(token_patterns))

        tokens = []
        last_pos = 0

        for match in master_pattern.finditer(query_input):
            start = match.start()
            if start > last_pos:
                literal_start = last_pos
                literal_end = match.start()
                literal_text = query_input[literal_start:literal_end].strip()

                if len(literal_text) != 0 and literal_text != " ":
                    tokens.append(Literal(literal_text, literal_start, literal_end))

            kind = match.lastgroup
            value = match.group()
            end = match.end()
            tokens.append(SimpleToken(TokenType[kind], start, start + len(value)))

            last_pos = end

        if last_pos < len(query_input):
            literal_text = query_input[last_pos:].strip()
            if len(literal_text) != 0 and literal_text != " ":
                tokens.append(Literal(literal_text, last_pos, len(query_input)))

        return tokens
