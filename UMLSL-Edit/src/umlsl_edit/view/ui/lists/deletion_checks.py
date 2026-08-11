"""
Shared deletion checks for cars and roads.

These helpers centralize deletion validation logic so UI components
can reuse the same rules.
"""

from typing import TYPE_CHECKING, Iterable, Optional

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import Road

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController


def get_car_deletion_block_reason(
    application_controller: "ApplicationController",
    car: Car,
) -> Optional[str]:
    """
    Returns a human-readable reason if the car cannot be deleted.
    Otherwise returns None.
    """
    queries = application_controller.command_controller.umlsl_queries_model.get_queries().values()
    related_queries = [
        query.latex for query in queries if query.assigned_car_uid == car.uid
    ]

    if related_queries:
        related_text = _format_bulleted_list(related_queries)
        return (
            f"Cannot delete car '{car.name}' because the following queries reference it "
            f"as ego cars:\n{related_text}"
        )

    return None


def get_road_deletion_block_reason(
    application_controller: "ApplicationController",
    road: Road,
) -> Optional[str]:
    """
    Returns a human-readable reason if the road cannot be deleted.
    Otherwise returns None.
    """
    cars = application_controller.data_controller.get_all_cars().values()
    cars_on_road = [car.name for car in cars if car.lane.road_uid == road.uid]

    if cars_on_road:
        cars_text = _format_bulleted_list(cars_on_road)
        return f"Cannot delete road '{road.name}' because the following cars are on it:\n{cars_text}"

    return None


def get_road_lane_change_block_reason(
    application_controller: "ApplicationController",
    road: Road,
    new_forward_lanes: int,
    new_backward_lanes: int,
) -> Optional[str]:
    """
    Returns a human-readable reason if the road's lane count cannot be reduced.
    Otherwise returns None.
    """
    if (
        new_forward_lanes >= road.number_of_forward_lanes
        and new_backward_lanes >= road.number_of_backward_lanes
    ):
        return None

    cars = application_controller.data_controller.get_all_cars().values()
    cars_blocking: list[str] = []

    for car in cars:
        if car.lane.road_uid != road.uid:
            continue

        lane_index = car.lane.lane_index
        if lane_index >= 0:
            if lane_index >= new_forward_lanes:
                cars_blocking.append(car.name)
        else:
            if lane_index < -new_backward_lanes:
                cars_blocking.append(car.name)

    if cars_blocking:
        cars_text = _format_bulleted_list(cars_blocking)
        return (
            f"Cannot update road '{road.name}' because the following cars are on lanes "
            f"that would be removed:\n{cars_text}"
        )

    return None


def _format_bulleted_list(items: Iterable[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
