import random

from dataclasses import dataclass
from typing import Tuple, List
from umlsl_sim.factories.create_cars import (
    create_goal,
    create_predefined_car,
    create_random_car,
    total_lane_segments,
)
from umlsl_sim.simulation.car import Car
from umlsl_sim.simulation.car_types import CarType
from umlsl_sim.simulation.event_checks import collision_check, reached_goal
from umlsl_sim.simulation.road_network.road_network import Direction, Road, Problem
from umlsl_sim.factories.create_segments import create_segments
from umlsl_sim.config.simulation_constants import DEADLOCK_FRAMES, WINNING_SCORE
from umlsl_sim.simulation.ports import CarController, CarControllerFactory
from umlsl_sim.simulation.reservations.reservation_management import ReservationManagement
from umlsl_sim.simulation.episode_history import GameHistory
from umlsl_sim.factories.car_spec import CarSpec


def _default_npc_controller_factory() -> CarControllerFactory:
    """The A* controller, imported only when no other factory was supplied.

    This is the one place the simulation layer names a concrete controller, and
    it is deliberately a *default* rather than a dependency: the import happens
    inside the function, so `umlsl_sim.simulation` still imports cleanly without
    `umlsl_sim.control`, and any caller that passes `npc_controller_factory`
    never reaches this code at all.
    """
    from umlsl_sim.control.astar.astar_car_controller import AstarCarController

    return AstarCarController


@dataclass(frozen=True)
class CarState:
    """One car's identity and outcome, as plain data.

    Kept separate from `Car` so it survives a `TrafficEnv.reset()`: the reset
    replaces every car object, so anything still holding the cars themselves
    would report the world the reset built rather than the one that just ran.

    Attributes:
        type (CarType): NPC or AGENT.
        name (str): The car's display name.
        score (int): Goals reached.
        dead (bool): Whether the car had crashed.
    """

    type: CarType
    name: str
    score: int
    dead: bool


class TrafficEnv:
    """
    A class to represent the traffic environment.

    Attributes:
        roads (List[Road]): List of roads in the environment.
        segments (List[Segment]): List of segments created from the roads.
        npcs (int): Number of npcs in the environment.
        agents (int): Number of ai controlled agents in the environment.
        controllers (List[CarController]): One controller per NPC, built by
            `npc_controller_factory`.
        moved (bool): Flag to indicate if a car has moved.
        time (int): Current time in the environment.
        stalled_frames (int): Consecutive frames on which every living car stood
            still.
    """

    def __init__(self,
                 roads: List[Road],
                 players: int,
                 predefined_cars: None | List[CarSpec] = None,
                 with_agent: bool = False,
                 npc_controller_factory: None | CarControllerFactory = None):
        """
        Initialize the TrafficEnv.

        Args:
            roads (List[Road]): List of roads in the environment.
            players (int): Total number of NPC cars in the environment. Any
                predefined NPC cars count toward this total — random NPCs are
                spawned to top up to `players`.
            predefined_cars (Optional[List[CarSpec]]): Optional scenario-supplied
                car specs. May include at most one car of type AGENT, which
                replaces the random agent car when `with_agent` is set.
            with_agent (bool): Whether to spawn an externally driven agent car
                alongside the NPCs. The environment neither knows nor cares what
                drives it -- an RL policy, a human, a scripted test -- only that
                `play_step` will be handed its action.
            npc_controller_factory (Optional[CarControllerFactory]): Builds the
                `CarController` for each NPC, as
                `factory(car, all_cars, reservation_management)`. Defaults to
                the A* controller; pass another to swap the NPC driving policy
                without touching the traffic logic.
        """
        super().__init__()
        self.roads = roads
        self.segments, self.intersections = create_segments(roads)
        self.npcs: int = players
        self.agent: bool = with_agent
        self.npc_controller_factory: CarControllerFactory = (
            npc_controller_factory if npc_controller_factory is not None
            else _default_npc_controller_factory()
        )

        self.predefined_cars: List[CarSpec] = list(predefined_cars) if predefined_cars else []
        agent_specs = [s for s in self.predefined_cars if s.type == CarType.AGENT]
        if len(agent_specs) > 1:
            raise ValueError(
                f"At most one predefined car of type AGENT is allowed; got {len(agent_specs)}"
            )
        self._predefined_agent: None | CarSpec = agent_specs[0] if agent_specs else None
        if self._predefined_agent is not None and not self.agent:
            raise ValueError(
                "Scenario defines a predefined AGENT car but `with_agent` is False; "
                "set with_agent=True or change the car type to NPC."
            )
        self._predefined_npcs: List[CarSpec] = [s for s in self.predefined_cars if s.type == CarType.NPC]
        if len(self._predefined_npcs) > self.npcs:
            raise ValueError(
                f"Scenario defines {len(self._predefined_npcs)} predefined NPCs "
                f"but `players` is {self.npcs}; reduce predefined NPCs or raise players."
            )

        # Randomly placed cars each need a lane segment of their own, so the
        # segment count is a hard ceiling. Check it here rather than letting
        # create_random_car fail partway through building the world.
        capacity = total_lane_segments(roads)
        needed = self.npcs + (1 if self.agent else 0)
        if needed > capacity:
            raise ValueError(
                f"This road network has {capacity} lane segments but {needed} cars "
                f"were requested ({self.npcs} players"
                f"{' + 1 RL agent' if self.agent else ''}). Lower `players` to at "
                f"most {capacity - (1 if self.agent else 0)}, or add roads/lanes."
            )

        # self.scores = None
        self.moved: bool = True
        self.time: int = 0
        self.stalled_frames: int = 0

        self.cars: List[Car] = []
        self.npc_cars: List[Car] = []
        self.agent_car: None | Car = None
        self.controllers: List[CarController] = []

        self.total_crashes: int = 0
        self.crashes: dict = {}

        self.reservation_management: ReservationManagement = ReservationManagement()
        self.game_history: GameHistory = GameHistory()

        self.reset()

    def reset(self) -> None:
        """
        Reset the environment to its initial state.
        """
        for intersection in self.intersections:
            intersection.intersection_state.reset()
            for crossing_segment in intersection.segments:
                crossing_segment.crossing_segment_state.reset()

        # init display
        self.moved = True
        self.time = 0
        self.stalled_frames = 0

        self.cars.clear()
        self.npc_cars.clear()
        self.agent_car = None
        self.controllers.clear()

        self.reservation_management.reset() 
        self.game_history.reset_history()

        if self.agent:
            if self._predefined_agent is not None:
                self.agent_car = create_predefined_car(
                    self._predefined_agent, self.roads, self.cars, self.reservation_management
                )
            else:
                self.agent_car = create_random_car(
                    self.roads, self.cars, CarType.AGENT, self.reservation_management
                )
            self.cars.append(self.agent_car)

        for spec in self._predefined_npcs:
            car = create_predefined_car(spec, self.roads, self.cars, self.reservation_management)
            self.cars.append(car)
            self.npc_cars.append(car)

        random_npcs_to_spawn = self.npcs - len(self._predefined_npcs)
        for _ in range(random_npcs_to_spawn):
            car = create_random_car(self.roads, self.cars, CarType.NPC, self.reservation_management)
            self.cars.append(car)
            self.npc_cars.append(car)

        for car in self.npc_cars:
            self.controllers.append(
                self.npc_controller_factory(car, self.cars, self.reservation_management)
            )

        self.game_history.set_list_of_cars(self.cars, self.reservation_management)
        self.game_history.set_map(self.roads)

        self.total_crashes = 0
        self.crashes = {Direction.RIGHT: 0, Direction.UP: 0, Direction.LEFT: 0, Direction.DOWN: 0}

    def play_step(self, action: None | Tuple[int, int] = None) -> None | str:
        """
        Execute a step in the environment for each car.

        Returns:
            bool: A boolean indicating if the game is over.
        """
        game_over = []

        if self.agent:
            if self.agent_car is not None and action is not None:
                game_over.append(
                    self._execute_action(car=self.agent_car, action=action) if not self.agent_car.get_death_status() else True
                )
                self.game_history.add_taken_action(self.agent_car, action)

        random.shuffle(self.controllers)
        actions: dict[Car, Tuple[int, int]] = dict()
        for controller in self.controllers:
            car = controller.car
            npc_action = controller.get_action()
            if not car.get_death_status():
                actions[car] = npc_action
            else:
                game_over.append(True)
        for car, action in actions.items():
            game_over.append(self._execute_action(car, action))
            self.game_history.add_taken_action(car, action)

        # A deadlock is a stall that does not resolve itself, so one frame of
        # standing traffic is not enough to declare one: count the consecutive
        # frames on which no car moves and report only once they reach
        # DEADLOCK_FRAMES. Any car moving resets the count.
        #
        # Only living cars have a say. A wreck is normally frozen at speed 0 and
        # would vote "stalled" either way, but not always: a car killed by an
        # earlier car's collision check this tick is already in `actions`, so
        # _execute_action still runs change_speed on it. move() then refuses
        # because it is dead, leaving a wreck parked at a non-zero speed for the
        # rest of the run -- which, counted, would suppress gridlock detection
        # from that point on. The list is also guarded against being empty,
        # where all() would vacuously report a stall.
        living_cars = [car for car in self.cars if not car.get_death_status()]
        if living_cars and all(car.speed == 0 for car in living_cars):
            self.stalled_frames += 1
        else:
            self.stalled_frames = 0

        # One tick per call, not one per car. `Car.time` -- which the crossing
        # time-to-leave arithmetic is expressed against -- advances by one for
        # every car on every step, so an environment clock that counted each
        # car's action separately ran len(cars) times faster than the cars it
        # was meant to be timing.
        self.time += 1

        if all(game_over):
            print("Game Over!")
            return 'game_over'
        if self.stalled_frames >= DEADLOCK_FRAMES:
            print("Deadlock!")
            return 'deadlock'

        return None
    
    def _execute_action(self, car: Car, action: Tuple[int, int]) -> bool:
        """
        Execute an action for a car.

        Returns:
            bool: A boolean indicating if the game is over for this car.
        """
        # update the head
        moved = self._move(car, action)

        # Check if the action was possible
        if isinstance(moved, Problem):
            if car is self.agent_car:
                car.illegal_move = True
            else:
                car.handle_car_death(self.reservation_management)
                return True

        # Crash detection:
        for other_car in self.cars:
            if other_car != car:
                if collision_check(car, other_car, self.reservation_management):
                    self.total_crashes += 1
                    self.crashes[car.direction] += 1
                    car.handle_car_death(self.reservation_management)
                    other_car.handle_car_death(self.reservation_management)
                    print(f"Collision Detected! {car.name} Car with {other_car.name} Car!")
                    return True

        # Place new goal if the goal is reached
        if reached_goal(car, self.reservation_management):
            car.score += 1
            car.goal = car.second_goal
            car_segment = self.reservation_management.get_car_reservation(car.id, 0).segment
            car.second_goal = create_goal(car.color, car_segment, self.roads, car.goal)

        # Player won!
        return car.score > WINNING_SCORE

    def _move(self, car: Car, action: Tuple[int, int]) -> bool | Problem:
        """
        Move the car based on the action.

        Args:
            car (Car): The car to move.
            action (Tuple[int, int]): The action to be executed.

        Returns:
            bool: True if the action was successful, False otherwise.
        """
        acceleration, lane_change = action
        car.change_speed(acceleration)

        action_worked = True
        if lane_change != 0:
            action_worked = action_worked and car.change_lane(self.reservation_management, lane_change, self.cars)

        action_worked = car.move(self.reservation_management) and action_worked

        return action_worked

    def car_states(self) -> List[CarState]:
        """Snapshot every car's identity, score and death status.

        Take one before an episode can be reset away if the state has to be
        reported afterwards -- see `CarState`.
        """
        return [
            CarState(car.type, car.name, car.score, car.get_death_status())
            for car in self.cars
        ]

    def current_state(self, states: None | List[CarState] = None) -> None:
        """Print the game state.

        Args:
            states (None | List[CarState]): What to print. Defaults to the live
                simulation; pass a `car_states()` snapshot to report an episode
                that has already been reset away.
        """
        if states is None:
            states = self.car_states()

        print("---------------------")
        print("Game State:\n")
        game_over = True

        for state in states:
            print(f"{state.type}: {state.name} | Score: {state.score} | Dead: {state.dead}")
            game_over = state.dead and game_over

        print(f"Game Over -> {game_over}")
        print("---------------------\n")

