"""A recorded episode: the world it ran in, and every action taken in it.

What is recorded is *actions*, not positions. A replay therefore re-drives the
recorded decisions through the same `Car` API the live simulation uses, on a
fresh reservation book -- it does not scrub through stored coordinates. That is
only reproducible if the state the cars started from is recorded too, which is
what `CarSnapshot` is for: `set_list_of_cars` takes the snapshot at the moment
`TrafficEnv.reset()` calls it, when the cars are in their initial state.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.ports import NullRenderer, Renderer
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.road_network.road_network import Color, Goal, LaneSegment, Road


class HistoryNotReplayable(RuntimeError):
    """Raised when a recording lacks the initial state a replay has to start from."""


@dataclass(frozen=True)
class CarSnapshot:
    """Everything needed to rebuild one car as it was when recording began.

    A `Car` does not hold its own segment -- that lives in the reservation book
    -- so a snapshot cannot be taken from the car alone, which is why
    `set_list_of_cars` wants the `ReservationManagement` alongside the cars.
    """

    key: str
    name: str
    type: CarType
    loc: int
    segment: LaneSegment
    speed: int
    size: int
    color: Color
    max_speed: int
    first_goal: Goal
    second_goal: Goal


class GameHistory():
    def __init__(self):
        self.map: List[Road] = list()
        self.list_of_cars: List[Car] = list()
        self.action_history_dict: Dict[str, List[Tuple[int, int]]] = dict()
        self.car_snapshots: List[CarSnapshot] = list()
        self.action_length = 0


    def set_list_of_cars(self, list_of_cars: List[Car],
                         reservation_management: Optional[ReservationManagement] = None) -> None:
        """Register the cars to record, and snapshot the state they start in.

        Args:
            list_of_cars (List[Car]): The cars of the episode about to run.
            reservation_management (Optional[ReservationManagement]): The book
                the cars are anchored in. Without it the cars are still
                recorded and their actions still collected, but the recording
                cannot be replayed -- there is nowhere else to read a car's
                starting segment from.
        """
        self.list_of_cars = list_of_cars.copy()
        self.car_snapshots = []

        for car in self.list_of_cars:
            self._create_new_car_entry(car)

        if reservation_management is None:
            return

        for car in self.list_of_cars:
            segment = reservation_management.get_car_reservation(car.id, 0).segment
            if not isinstance(segment, LaneSegment):
                # A car mid-crossing has no lane segment to be rebuilt on. That
                # cannot happen at reset, but it does when a recording is
                # restored from a pickle of end-of-episode cars.
                self.car_snapshots = []
                return
            self.car_snapshots.append(CarSnapshot(
                key=self._car_entry_key(car),
                name=car.name,
                type=car.type,
                loc=car.loc,
                segment=segment,
                speed=car.speed,
                size=car.size,
                color=car.color,
                max_speed=car.max_speed,
                first_goal=car.goal,
                second_goal=car.second_goal,
            ))


    def set_map(self, roads: List[Road]) -> None:
        self.map = roads.copy()


    def set_action_history_dict(self, action_history_dict: Dict) -> None:
        self.action_history_dict = action_history_dict


    def add_taken_action(self, car: Car, action: Tuple[int, int]) -> None:
        key = self._car_entry_key(car)
        actions = self.action_history_dict.get(key)
        if actions is None:
            raise KeyError(
                f"No history entry for car {car.id!r}; call set_list_of_cars "
                f"with every car that will act before recording actions."
            )
        actions.append(action)
        self.action_length += 1


    def _create_new_car_entry(self, car: Car) -> None:
        self.action_history_dict[self._car_entry_key(car)] = list()


    def _car_entry_key(self, car: Car) -> str:
        """The per-car key of the action history.

        Keyed on `car.id`, which carries a monotonic counter and so is unique
        even when two cars share a display name -- a scenario is free to name
        two predefined cars alike, and a name-keyed history would have silently
        merged their action lists into one and mis-attributed every replay.
        """
        return f"{car.type.name}:{car.id}"


    def replay(self, renderer: "Renderer | None" = None) -> None:
        """Re-drive the recorded actions from the state the episode started in.

        The replay is the same loop whether or not anyone is watching: a
        `Renderer` is where the frames go, and the default one throws them away.
        Nothing here knows what a window is -- pass
        `umlsl_sim.simulation.ports.create_renderer(RenderMode.GUI, ...)` to see it.

        Cars are rebuilt from `car_snapshots` on a reservation book of their
        own, so a replay neither reads nor disturbs the reservations of a live
        simulation, and replaying twice gives the same run both times. One frame
        is drawn per tick, after every car has taken its action for that tick.

        Args:
            renderer (Renderer | None): Where to draw each frame. Defaults to a
                `NullRenderer`, which replays the episode headlessly.

        Raises:
            HistoryNotReplayable: If no initial state was recorded -- either
                `set_list_of_cars` was called without a `ReservationManagement`,
                or the recording was restored from a save format that does not
                carry one (see `rl_io.create_game_history`).
        """
        renderer = renderer if renderer is not None else NullRenderer()

        if not self.car_snapshots:
            raise HistoryNotReplayable(
                "This recording has no initial car state, so there is nothing to "
                "replay from. Pass the ReservationManagement to set_list_of_cars "
                "when recording."
            )

        reservation_management = ReservationManagement()
        cars: List[Car] = []
        actions_by_car: List[List[Tuple[int, int]]] = []
        for snapshot in self.car_snapshots:
            cars.append(Car(name=snapshot.name,
                            type=snapshot.type,
                            loc=snapshot.loc,
                            segment=snapshot.segment,
                            speed=snapshot.speed,
                            size=snapshot.size,
                            color=snapshot.color,
                            max_speed=snapshot.max_speed,
                            first_goal=snapshot.first_goal,
                            second_goal=snapshot.second_goal,
                            reservation_management=reservation_management))
            actions_by_car.append(list(self.action_history_dict.get(snapshot.key, [])))

        renderer.bind(cars, self.map, reservation_management)

        ticks = max((len(actions) for actions in actions_by_car), default=0)
        for i in range(ticks):
            for car, actions in zip(cars, actions_by_car):
                if i >= len(actions):
                    # This car stopped acting earlier than the others -- it
                    # crashed, or won -- so it simply takes no turn.
                    continue
                acceleration, lane_change = actions[i]

                car.change_speed(acceleration)
                if lane_change != 0:
                    car.change_lane(reservation_management, lane_change, cars)
                car.move(reservation_management)

            renderer.draw_frame()

        renderer.close()

    def reset_history(self) -> None:
        self.map.clear()
        self.list_of_cars.clear()
        self.action_history_dict.clear()
        self.car_snapshots.clear()
        self.action_length = 0
