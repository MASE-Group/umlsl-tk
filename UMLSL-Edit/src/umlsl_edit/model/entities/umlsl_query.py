from dataclasses import dataclass

from umlsl_edit.model.entities.entity import Entity
from umlsl_edit.model.errors.umlsl_query_errors import UMLSLQueryValidationError
from umlsl_edit.model.helpers.uid_service import generate_uid


@dataclass(frozen=True)
class UMLSLQueryParams:
    """
    Dataclass representing parameters for creating a UMLSL query.

    Attributes:
        latex (str): The UMLSL query in LaTeX format.
        assigned_car_uid (str): The name of the car associated with the query.
        holding (str): Whether the UMLSL query is holding or not.
    """
    latex: str
    assigned_car_uid: str
    should_only_evaluate_on_cars_lane: bool
    holding: bool = False


@dataclass()
class UMLSLQuery(Entity):
    """Dataclass representing a UMLSL query.

    Attributes:
        uid (str): The unique identifier of the UMLSL query.
        latex (str): The UMLSL query in LaTeX format.
        assigned_car_uid (str): The name of the car associated with the query.
        validation (bool): A flag indicating whether the query is true of false in the current context.

    Raises:
        UMLSLQueryValidationError: If any validation check fails.
    """
    latex: str
    assigned_car_uid: str
    should_only_evaluate_on_cars_lane: bool
    holding: bool

    @classmethod
    def from_params(cls, params: UMLSLQueryParams) -> "UMLSLQuery":
        """
        Creates a UMLSLQuery instance from a UMLSLQueryParams dataclass.

        Args:
            params: UMLSLQueryParams instance containing all UMLSL query attributes.
        """
        return cls(
            uid=generate_uid(),
            latex=params.latex,
            assigned_car_uid=params.assigned_car_uid,
            should_only_evaluate_on_cars_lane=params.should_only_evaluate_on_cars_lane,
            holding=False
        )

    def update_from_params(self, params: UMLSLQueryParams) -> None:
        """
        Updates the UMLSLQuery instance's attributes based on a UMLSLQueryParams object.

        Args:
            params: An instance of UMLSLQueryParams containing the new UMLSL query attributes.
        """
        self.latex = params.latex
        self.assigned_car_uid = params.assigned_car_uid
        self.should_only_evaluate_on_cars_lane = params.should_only_evaluate_on_cars_lane
        self.holding = params.holding
        self.__post_init__()

    def __post_init__(self) -> None:
        """
        Validates the UMLSLQuery instance after initialization.

        Raises:
            UMLSLQueryValidationError: If any validation check fails.
        """
        self.validate()
        self._initialized = True

    def __setattr__(self, name: str, value: object) -> None:
        super().__setattr__(name, value)
        if getattr(self, "_initialized", False):
            self.validate()

    def validate(self) -> None:
        if not isinstance(self.latex, str) or not self.latex.strip():
            raise UMLSLQueryValidationError("Latex query must be a non-empty string.")

        if not isinstance(self.assigned_car_uid, str) or not self.assigned_car_uid.strip():
            raise UMLSLQueryValidationError("Assigned car name must be a non-empty string.")

        if not isinstance(self.holding, bool):
            raise UMLSLQueryValidationError("Validation must be a boolean.")

        if not isinstance(self.should_only_evaluate_on_cars_lane, bool):
            raise UMLSLQueryValidationError("should_only_evaluate_on_cars_lane must be a boolean.")
