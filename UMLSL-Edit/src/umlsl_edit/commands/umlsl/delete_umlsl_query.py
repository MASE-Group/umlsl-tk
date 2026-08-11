from umlsl_edit.commands.command import Command
from umlsl_edit.model.domain_models.umlsl_queries_model import UMLSLQueriesModel


class DeleteUMLSLQuery(Command[None]):
    """Deletes a UMLSL query from the model based on its unique identifier."""

    def __init__(
            self,
            query_id: str,
            umlsl_queries_model: UMLSLQueriesModel
    ):
        """
        Initialize the DeleteUMLSLQuery command.

        Args:
            query_id: Unique identifier of the query to be deleted.
            umlsl_queries_model: The model to remove the query from.
        """
        self.query_id = query_id
        self.umlsl_queries_model = umlsl_queries_model

    def execute(self) -> None:
        """
        Deletes the query with the specified unique identifier from the model.

        Raises:
            UMLSLQueriesValidationError: If the query does not exist.
        """

        self.umlsl_queries_model.get_query_by_id(self.query_id)
        self.umlsl_queries_model.remove_umlsl_query(self.query_id)
