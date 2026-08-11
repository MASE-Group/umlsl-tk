import asyncio
from enum import Enum
from typing import Any

from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery, UMLSLQueryParams
from umlsl_edit.model.errors.umlsl_query_errors import (
    UMLSLQueryValidationError,
)
from umlsl_edit.model.helpers.event_types import (
    TrafficSnapshotEventType,
    UMLSLQueriesEventType,
)
from umlsl_edit.model.helpers.observables import Observable, ObservableDict


class UMLSLQueriesValidationError(Exception):
    """Raised when UMLSL queries validation fails in the context of a traffic snapshot."""

    pass


class UMLSLQueriesModel(Observable):
    """
    UMLSL queries model using Observable pattern.

    Events:
        - UMLSLQueriesEventType.UMLSL_QUERY_ADDED: Fired when a query is added (data: UMLSLQuery)
        - UMLSLQueriesEventType.UMLSL_QUERY_REMOVED: Fired when a query is removed (data: UMLSLQuery)
        - UMLSLQueriesEventType.UMLSL_QUERY_UPDATED: Fired when a query is updated (data: UMLSLQuery)
    """

    def __init__(
            self,
            traffic_snapshot: TrafficSnapshotModel,
            queries: dict[str, UMLSLQuery] = None,
    ) -> None:
        super().__init__()
        self._active_futures = {}
        self.queries = ObservableDict(
            on_add=lambda query: self.notify(
                UMLSLQueriesEventType.UMLSL_QUERY_ADDED, query
            ),
            on_remove=lambda query: self.notify(
                UMLSLQueriesEventType.UMLSL_QUERY_REMOVED, query
            ),
            on_update=lambda query: self.notify(
                UMLSLQueriesEventType.UMLSL_QUERY_UPDATED, query
            ),
            initial_data=queries,
        )
        self._traffic_snapshot = traffic_snapshot

        self._traffic_snapshot.attach(self._on_traffic_snapshot_event)

    def _on_traffic_snapshot_event(self, event_type: Enum, data) -> None:
        if (
                event_type == TrafficSnapshotEventType.CAR_ADDED
                or event_type == TrafficSnapshotEventType.CAR_UPDATED
                or event_type == TrafficSnapshotEventType.CAR_REMOVED
                or event_type == TrafficSnapshotEventType.ROAD_ADDED
                or event_type == TrafficSnapshotEventType.ROAD_REMOVED
                or event_type == TrafficSnapshotEventType.ROAD_UPDATED
                or event_type == TrafficSnapshotEventType.SNAPSHOT_RELOADED
        ):
            self.revalidate_queries()

    def get_query_by_id(self, uid: str) -> UMLSLQuery:
        if uid not in self.queries:
            raise UMLSLQueryValidationError(
                f"UMLSL Query with UID {uid} does not exist."
            )
        return self.queries[uid]

    def get_queries(self) -> dict[str, UMLSLQuery]:
        """Return all UMLSL queries as a plain dictionary."""
        return dict(self.queries.__dict__())

    def add_umlsl_query(self, umlsl_query: UMLSLQuery) -> None:
        """
        Adds a UMLSL query to the snapshot and validates all attributes in the context of the snapshot.
        Raises:
            TrafficSnapshotValidationError: If the UMLSL query is invalid in the context of the snapshot.
        """
        self.queries[umlsl_query.uid] = umlsl_query
        self.revalidate_queries()

    def remove_umlsl_query(self, query_id: str) -> None:
        """
        Removes a UMLSL query from the snapshot.
        """
        self.queries.pop(query_id)
        self.revalidate_queries()

    def update_umlsl_query(
            self,
            umlsl_query_data: UMLSLQuery,
            query_params: UMLSLQueryParams,
            revalidate_queries: bool = True,
    ) -> None:
        """
        Updates an existing UMLSL query in the snapshot and validates all attributes in the context of the snapshot.

        Raises:
            UMLSLQueriesValidationError: If the updated UMLSL query is invalid in the context of the snapshot.
        """
        umlsl_query_data.update_from_params(query_params)
        self.queries[umlsl_query_data.uid] = umlsl_query_data
        if revalidate_queries:
            self.revalidate_queries()

    def mark_umlsl_query_as_loading(self, query: UMLSLQuery) -> None:
        self.notify(UMLSLQueriesEventType.UMLSL_QUERY_LOADING, query)

    def revalidate_queries(self):

        from umlsl_edit.query.evaluation_worker import evaluate_query_worker

        self._traffic_snapshot.validator.validate_queries(self)

        self._traffic_snapshot.evaluation_version += 1
        current_version = self._traffic_snapshot.evaluation_version

        snapshot_dict = self._traffic_snapshot.to_dict()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None

        for query in self.queries.values():
            ego = self._traffic_snapshot.cars.get(query.assigned_car_uid)
            if ego is None:
                continue

            if query.uid in self._active_futures:
                self._active_futures[query.uid].cancel()

            self.mark_umlsl_query_as_loading(query)

            evaluate_ego_lane_only = query.should_only_evaluate_on_cars_lane

            def on_evaluation_done(fut, q=query, v=current_version):
                # The result is applied before the future is dropped, so an empty
                # _active_futures means every result has already been written back.
                try:
                    if v != self._traffic_snapshot.evaluation_version:
                        return
                    if fut.cancelled():
                        return
                    holding = fut.result()
                    new_query_params = UMLSLQueryParams(
                        latex=q.latex,
                        holding=holding,
                        should_only_evaluate_on_cars_lane=q.should_only_evaluate_on_cars_lane,
                        assigned_car_uid=q.assigned_car_uid,
                    )

                    # if (
                    #         q.holding != new_query_params.holding
                    #         or q.latex != new_query_params.latex
                    #         or q.assigned_car_uid != new_query_params.assigned_car_uid
                    # ):
                    self.update_umlsl_query(
                        q, new_query_params, revalidate_queries=False
                    )
                except Exception as e:
                    print(f"Evaluation failed: {e}")
                finally:
                    if self._active_futures.get(q.uid) is fut:
                        del self._active_futures[q.uid]

            if loop is not None and loop.is_running():
                future = loop.run_in_executor(
                    self._traffic_snapshot.process_pool,
                    evaluate_query_worker,
                    snapshot_dict,
                    query.latex,
                    ego.uid,
                    evaluate_ego_lane_only,
                    self._traffic_snapshot.settings_model.braking_acceleration,
                    self._traffic_snapshot.settings_model.max_speed,
                )
                self._active_futures[query.uid] = future
                future.add_done_callback(on_evaluation_done)
            else:
                future = self._traffic_snapshot.process_pool.submit(
                    evaluate_query_worker,
                    snapshot_dict,
                    query.latex,
                    ego.uid,
                    evaluate_ego_lane_only,
                    self._traffic_snapshot.settings_model.braking_acceleration,
                    self._traffic_snapshot.settings_model.max_speed,
                )
                self._active_futures[query.uid] = future
                future.add_done_callback(on_evaluation_done)

    def to_dict(self) -> list[dict[str, Any]]:
        """
        Serializes the UMLSL_queries instance to a list of dictionaries suitable for JSON encoding.
        """
        return [
            {
                "uid": query.uid,
                "latex": query.latex,
                "should_only_evaluate_on_cars_lane": query.should_only_evaluate_on_cars_lane,
                "assigned_car_uid": query.assigned_car_uid,
            }
            for query in self.queries.__dict__().values()
        ]

    def to_json(self) -> str:
        """
        Serializes the UMLSL_queries instance to a JSON string.
        """
        import json

        return json.dumps(self.to_dict(), indent=2)

    def clear(self) -> None:
        """Remove all queries."""
        for query_id in list(self.queries.__dict__().keys()):
            self.queries.pop(query_id)

    def from_dict(self, data: list[dict[str, Any]]) -> None:
        """
        Loads queries from a list of dictionaries.

        Args:
            data: A list containing query dictionaries.
        """
        if not isinstance(data, list):
            raise ValueError("Queries payload must be a list.")
        self.clear()
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("Each query must be a dictionary.")
            params = UMLSLQueryParams(
                latex=entry["latex"],
                assigned_car_uid=entry["assigned_car_uid"],
                should_only_evaluate_on_cars_lane=entry[
                    "should_only_evaluate_on_cars_lane"
                ],
            )
            query = UMLSLQuery.from_params(params)
            if "uid" in entry:
                query.uid = entry["uid"]
            self.add_umlsl_query(query)

    def from_json(self, json_string: str) -> None:
        """
        Loads queries from a JSON string.

        Args:
            json_string: A JSON-formatted string containing umlsl query data.
        """
        import json

        data = json.loads(json_string)
        self.from_dict(data)
