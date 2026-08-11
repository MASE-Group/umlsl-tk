from abc import ABC
from dataclasses import dataclass


@dataclass
class Entity(ABC):
    """Abstract base class for all entities in the UMLSL editor."""
    uid: str

    def __eq__(self, other):
        """Checks equality based only on the entity's unique identifier."""
        if not isinstance(other, Entity):
            return False
        return self.uid == other.uid


    def __hash__(self):
        """Generates a hash based only on the entity's unique identifier."""
        return hash(self.uid)
