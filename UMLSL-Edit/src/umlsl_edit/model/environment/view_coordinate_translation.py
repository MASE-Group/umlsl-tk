import typing
from collections.abc import Callable
from dataclasses import dataclass

from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.interval import Interval
from umlsl_edit.model.traffic_value_objects.segments.segment import Segment
from umlsl_edit.model.traffic_value_objects.segments.segment_interval import SegmentInterval
from umlsl_edit.model.traffic_value_objects.segments.virtual_lane import VirtualLane

if typing.TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


@dataclass(frozen=True)
class CoordinateTranslation:
    """
    Includes information about how a fixed car perceives visible, reserved, and claimed information of all cars.

    Attributes:
        visible: maps each car to a map that equips each visible segment with its interval information
        reserved: maps each car to a map that equips each reserved segment with its interval information
        claimed: maps each car to a map that equips each claimed segment with its interval information
    """
    visible: dict[str, dict[Segment, Interval]]
    reserved: dict[str, dict[Segment, Interval]]
    claimed: dict[str, dict[Segment, Interval]]


def translate_into_ego_coordinates(
        ts: "TrafficSnapshotModel", ego: Car, horizontal_horizon: Interval, virtual_lanes: list[VirtualLane]
) -> CoordinateTranslation:
    """
    Translates all visible, reserved, and claimed information of all cars into the coordinate system of ego depending
    on the given list of virtual lanes ("the not yet constructed View").
    """

    def translate_coordinate_system(
            segments_of_car: Callable[[Car], list[SegmentInterval]]
    ) -> dict[str, dict[Segment, Interval]]:
        translated: dict[str, dict[Segment, Interval]] = {}
        for perceived_car in ts.get_car_list():
            translated[perceived_car.uid] = ego.environment.translate_interval_coordinates(
                virtual_lanes,
                horizontal_horizon,
                segments_of_car(perceived_car),
                perceived_car,
                ts
            )
        return translated

    # translate physical, reserved and claimed intervals of every car into the coordinate system of ego
    visible_cars: dict[str, dict[Segment, Interval]] = translate_coordinate_system(
        lambda c: c.environment.physical_segment_intervals)
    reserved_segments: dict[str, dict[Segment, Interval]] = translate_coordinate_system(
        lambda c: c.environment.reserved)
    claimed_segments: dict[str, dict[Segment, Interval]] = translate_coordinate_system(
        lambda c: c.environment.claimed
    )

    """
    DEBUG:
    print("evaluating parallel virtual lane with horizon ", horizontal_horizon.start, horizontal_horizon.end)
    print("visible cars: ")
    for visible_car in visible_cars:
        print(">", ts.cars[visible_car].name, ":")
        for segment, interval in visible_cars[visible_car].items():
            print(f"  {ts.get_segment_info(segment.uid)}: {interval}")
    print("")
    print("reserved cars: ")
    for intersecting_car in reserved_segments:
        print(">", ts.cars[intersecting_car].name, ":")
        for segment, interval in reserved_segments[intersecting_car].items():
            print(f"  {ts.get_segment_info(segment.uid)}: {interval}")
    """

    return CoordinateTranslation(visible_cars, reserved_segments, claimed_segments)
