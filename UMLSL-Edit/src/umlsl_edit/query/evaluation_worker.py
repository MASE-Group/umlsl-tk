import traceback
from typing import Any, Dict


def evaluate_query_worker(
        snapshot_dict: Dict[str, Any],
        latex: str,
        ego_uid: str,
        evaluate_ego_lane_only: bool,
        braking_acceleration: float,
        max_speed: float,
) -> bool:
    """
    Worker function to evaluate a UMLSL query in a separate process.
    """
    from umlsl_edit.model.domain_models.settings_model import SettingsModel
    from umlsl_edit.model.domain_models.traffic_snapshot_model import (
        TrafficSnapshotModel,
    )
    from umlsl_edit.query.evaluator import UMLSLEvaluator

    try:
        settings_model = SettingsModel(
            braking_acceleration=braking_acceleration, max_speed=max_speed
        )

        snapshot = TrafficSnapshotModel(
            settings_model=settings_model
        )

        # Reconstruct the snapshot from the dictionary. No UMLSLQueriesModel is
        # attached here: the worker evaluates a single formula and must not kick
        # off a revalidation of its own.
        TrafficSnapshotModel.from_dict(
            snapshot_dict, snapshot, snapshot, settings_model
        )

        umlsl_evaluator = UMLSLEvaluator(snapshot)
        ego = snapshot.get_cars().get(ego_uid)

        if ego is None:
            return False

        holding = umlsl_evaluator.parse_ast(latex, ego).evaluate(evaluate_ego_lane_only)
        return holding
    except Exception as e:
        print(f"Error evaluating query in worker: {e}")
        traceback.print_exc()
        return False
