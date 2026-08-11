from __future__ import annotations

from typing import Any

from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.domain_models.traffic_snapshot_reader import (
    TrafficSnapshotReader,
)
from umlsl_edit.model.domain_models.traffic_snapshot_writer import (
    TrafficSnapshotWriter,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)


class PersistenceService:
    """Handles saving/loading JSON payloads for traffic snapshots and UMLSL queries."""

    VERSION = 2

    @staticmethod
    def serialize(
        snapshot: TrafficSnapshotModel,
        queries: UMLSLQueriesModel,
    ) -> dict[str, Any]:
        """
        Serialize snapshot and queries to a JSON-ready dict.

        Returns:
            Dict payload containing roads, cars, queries, and meta version.
        """
        snapshot_data = snapshot.to_dict()
        if not isinstance(snapshot_data, dict):
            raise ValueError("TrafficSnapshotModel.to_dict() must return a dict.")

        roads = snapshot_data.get("roads")
        cars = snapshot_data.get("cars")

        if roads is None or cars is None:
            raise ValueError("TrafficSnapshotModel.to_dict() must contain 'roads' and 'cars' keys.")

        queries_data = queries.to_dict()

        return {
            "meta": {"version": PersistenceService.VERSION},
            "roads": roads,
            "cars": cars,
            "queries": queries_data,
        }

    @staticmethod
    def deserialize(
        data: dict[str, Any],
        traffic_snapshot_writer: TrafficSnapshotWriter,
        traffic_snapshot_reader: TrafficSnapshotReader,
        settings_model: SettingsModel,
        umlsl_queries_model: UMLSLQueriesModel,
    ) -> None:
        """
        Populate snapshot and queries from a JSON-ready dict.

        This validates the schema minimally and ensures queries reference existing cars.
        """
        if not isinstance(data, dict):
            raise ValueError("Snapshot payload must be a JSON object.")

        meta = data.get("meta", {})
        if meta:
            if not isinstance(meta, dict):
                raise ValueError("Snapshot 'meta' must be an object.")
            version = meta.get("version", PersistenceService.VERSION)
            if version != PersistenceService.VERSION:
                raise ValueError(f"Unsupported snapshot version: {version}")

        roads = data.get("roads", [])
        cars = data.get("cars", [])
        queries = data.get("queries", [])

        if not isinstance(roads, list):
            raise ValueError("Snapshot 'roads' must be a list.")
        if not isinstance(cars, list):
            raise ValueError("Snapshot 'cars' must be a list.")
        if not isinstance(queries, list):
            raise ValueError("Snapshot 'queries' must be a list.")

        TrafficSnapshotModel.from_dict(
            {"roads": roads, "cars": cars},
            traffic_snapshot_writer,
            traffic_snapshot_reader,
            settings_model
        )

        existing_car_uids = set(traffic_snapshot_reader.get_cars().keys())
        filtered_queries: list[dict[str, Any]] = []

        for query in queries:
            if not isinstance(query, dict):
                raise ValueError("Each query must be an object.")

            assigned_car_uid = query.get("assigned_car_uid")
            if assigned_car_uid is None and "assigned_car_name" in query:
                car = traffic_snapshot_reader.get_car_by_name(query["assigned_car_name"])
                assigned_car_uid = car.uid if car else None

            if assigned_car_uid in existing_car_uids:
                normalized = dict(query)
                normalized["assigned_car_uid"] = assigned_car_uid
                filtered_queries.append(normalized)

        umlsl_queries_model.from_dict(filtered_queries)
