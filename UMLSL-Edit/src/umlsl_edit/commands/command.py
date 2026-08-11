from abc import ABC, abstractmethod
from typing import TypeVar, Generic

ReturnValue = TypeVar('ReturnValue')

class CommandValidationError(ValueError):
    """Exception raised when a command fails validation."""
    pass

class Command(ABC, Generic[ReturnValue]):
    """Interface for commands that can be executed in the UMLSL editor."""
    @abstractmethod
    def execute(self) -> ReturnValue:
        """Executes the command and returns a value of type ReturnValue assuming the state of the command is validated
        and executes successfully."""