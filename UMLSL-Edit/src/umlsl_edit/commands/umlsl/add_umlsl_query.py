from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery, UMLSLQueryParams
from umlsl_edit.model.errors.umlsl_query_errors import (
    UMLSLQueryValidationError,
)


class AddUMLSLQuery(Command[None]):
    """Creates a UMLSL query object based on the provided parameters and adds it to the model."""

    def __init__(
            self,
            umlsl_query_params: UMLSLQueryParams,
            umlsl_queries_model: UMLSLQueriesModel,
            traffic_snapshot_reader: TrafficSnapshotReader
    ):
        """
        Initialize the AddUMLSLQuery command.

        Args:
            umlsl_query_params: Parameters for creating the query.
            umlsl_queries_model: The model to add the query to.
        """
        self.umlsl_query_params = umlsl_query_params
        self.umlsl_queries_model = umlsl_queries_model
        self.traffic_snapshot_reader = traffic_snapshot_reader

    def execute(self) -> None:
        """
        Creates a UMLSLQuery instance and adds it to the model.

        Raises:
            UMLSLQueryValidationError: If query validation fails.
        """
        if not self.traffic_snapshot_reader.is_car_existing(self.umlsl_query_params.assigned_car_uid):
            raise UMLSLQueryValidationError("Assigned car does not exist in the current traffic snapshot.")
        umlsl_query = UMLSLQuery.from_params(self.umlsl_query_params)
        self.umlsl_queries_model.add_umlsl_query(umlsl_query)
