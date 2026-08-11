from typing import TYPE_CHECKING

from umlsl_edit.model.entities.car import Car, CarParams
from umlsl_edit.model.entities.road import Road
from umlsl_edit.model.errors.car_errors import CarTrafficSnapshotContextValidationError
from umlsl_edit.model.helpers.event_types import TrafficSnapshotEventType

if TYPE_CHECKING:
    from umlsl_edit.model.domain_models.traffic_snapshot_model import TrafficSnapshotModel


class CarMixin:
    def is_car_existing(self: "TrafficSnapshotModel", uid: str) -> bool:
        return uid in self.cars

    def validate_car_params(
            self: "TrafficSnapshotModel", car_params: CarParams, new_instantiation: bool, car_uid: str | None = None
    ) -> None:
        self.validator.validate_car_params(car_params, new_instantiation, car_uid)

    def _on_car_added(self: "TrafficSnapshotModel", car: Car):
        self.notify(TrafficSnapshotEventType.CAR_ADDED, car)

    def _on_car_removed(self: "TrafficSnapshotModel", car: Car):
        self.notify(TrafficSnapshotEventType.CAR_REMOVED, car)

    def _on_car_updated(self: "TrafficSnapshotModel", car: Car):
        self.notify(TrafficSnapshotEventType.CAR_UPDATED, car)

    def get_cars_on_road(self: "TrafficSnapshotModel", road: Road) -> list[Car]:
        return [car for car in self.cars.values() if car.lane.road_uid == road.uid]

    def get_cars(self: "TrafficSnapshotModel") -> dict[str, Car]:
        return dict(self.cars)

    def get_car_list(self: "TrafficSnapshotModel") -> list[Car]:
        return list(self.cars.values())

    def get_car_by_name(self: "TrafficSnapshotModel", name: str) -> Car | None:
        for car in self.cars.values():
            if car.name == name:
                return car
        return None

    def add_car(self: "TrafficSnapshotModel", car: Car) -> None:
        car_params = CarParams(
            name=car.name,
            lane=car.lane,
            color=car.color,
            position_on_lane=car.position_on_lane,
            transition=car.transition,
            speed=car.speed,
            length=car.length,
            next_turn=car.next_turn,
            acceleration=car.acceleration,
        )
        self.validate_car_params(car_params, True)
        if self.is_car_existing(car.uid):
            raise ValueError(f"Car with uid {car.uid} already exists.")
        self.cars[car.uid] = car
        self._revalidate_cars()

    def remove_car(self: "TrafficSnapshotModel", car_uid: str) -> None:
        self.cars.pop(car_uid)
        self._revalidate_cars()

    def update_car_with_params(self: "TrafficSnapshotModel", car_uid: str, car_params: CarParams) -> None:
        car = self.cars.get(car_uid)
        if car is None:
            raise ValueError(f"Car with uid {car_uid} not found.")
        self.validate_car_params(car_params, False, car_uid)
        existing = self.get_car_by_name(car_params.name)
        if existing is not None and existing.uid != car_uid:
            raise CarTrafficSnapshotContextValidationError(
                content=f"Car name '{car_params.name}' is not unique in the traffic snapshot."
            )
        car.update_from_params(car_params, self, self.settings_model)
        self.cars[car_uid] = car
        self._revalidate_cars()

    def _revalidate_cars(self: "TrafficSnapshotModel"):
        cars_to_remove = []
        cars_snapshot = list(self.cars.values())
        for car in cars_snapshot:
            if not self.validator.validate_car_and_autocorrect(car):
                cars_to_remove.append(car)
                continue

            car.recalculate_environment(
                self,
                settings_model=self.settings_model,
            )
            self.cars[car.uid] = car

        for car in cars_to_remove:
            del self.cars[car.uid]
