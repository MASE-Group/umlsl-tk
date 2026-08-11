import json
import os
import tempfile
import time
import unittest
from threading import Event, Lock

from umlsl_edit.commands.persistence.load_traffic_snapshot import (
    LoadTrafficSnapshot,
)
from umlsl_edit.controllers.command_controller import CommandController
from umlsl_edit.controllers.data_controller import DataController
from umlsl_edit.controllers.event_controller import EventController
from umlsl_edit.model.domain_models.settings_model import SettingsModel
from umlsl_edit.model.domain_models.traffic_snapshot_model import (
    TrafficSnapshotModel,
)
from umlsl_edit.model.domain_models.umlsl_queries_model import (
    UMLSLQueriesModel,
)
from umlsl_edit.model.entities.road import RoadOrientation
from umlsl_edit.query.evaluator import UMLSLEvaluator
from umlsl_edit.services.persistence_service import PersistenceService


class FakeSignal:
    def __init__(self):
        self.values = []

    def emit(self, value):
        self.values.append(value)


class FakeViewEventHandler:
    def __init__(self):
        self._snapshot_changed_signal = FakeSignal()

    def get_on_snapshot_changed_signal(self):
        return self._snapshot_changed_signal


class FakeAppController:
    def __init__(self, settings_model: SettingsModel):
        self._settings_model = settings_model
        self.view_event_handler = FakeViewEventHandler()
        self.replaced_snapshot = None
        self.replaced_queries = None

    def get_settings_model(self):
        return self._settings_model

    def replace_snapshot(self, traffic_snapshot, umlsl_queries):
        self.replaced_snapshot = traffic_snapshot
        self.replaced_queries = umlsl_queries


class SpyView:
    def __init__(self):
        self.added_cars = []
        self.removed_cars = []
        self.updated_cars = []
        self.added_roads = []
        self.removed_roads = []
        self.updated_roads = []
        self.added_queries = []
        self.removed_queries = []
        self.updated_queries = []
        self.warnings = []
        self.snapshot_reloaded = []
        self.loading_queries = []
        self.revalidation_started_count = 0
        self.revalidation_finished_count = 0
        self._revalidation_event = Event()
        self._revalidation_lock = Lock()

    def add_car_view(self, car):
        self.added_cars.append(car)

    def remove_car_view(self, car):
        self.removed_cars.append(car)

    def update_car_view(self, car):
        self.updated_cars.append(car)

    def add_road_view(self, road):
        self.added_roads.append(road)

    def remove_road_view(self, road):
        self.removed_roads.append(road)

    def update_road_view(self, road):
        self.updated_roads.append(road)

    def add_query_view(self, query):
        self.added_queries.append(query)

    def remove_query_view(self, query):
        self.removed_queries.append(query)

    def update_query_view(self, query):
        self.updated_queries.append(query)

    def loading_query_view(self, data):
        self.loading_queries.append(data)

    def revalidation_started(self):
        with self._revalidation_lock:
            self.revalidation_started_count += 1
            self._revalidation_event.clear()

    def revalidation_finished(self):
        with self._revalidation_lock:
            self.revalidation_finished_count += 1
            self._revalidation_event.set()

    def reset_revalidation_event(self):
        self._revalidation_event.clear()

    def wait_for_revalidation(self, timeout=1.0):
        return self._revalidation_event.wait(timeout)

    def display_warning(self, warning):
        self.warnings.append(warning)

    def on_snapshot_reloaded(self, snapshot, queries=None):
        self.snapshot_reloaded.append((snapshot, queries))


def wait_until(predicate, timeout=1.0, interval=0.01):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def wait_for_evaluations(queries, timeout=60.0, interval=0.01):
    """
    Block until every query evaluation dispatched to the process pool has been
    written back to its query.

    Use this instead of polling ``holding`` with ``wait_until`` when a query is
    expected *not* to hold: ``wait_until`` can only conclude "false" by burning
    its whole timeout, whereas a settled evaluation can be asserted on directly.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not queries._active_futures:
            return True
        time.sleep(interval)
    return not queries._active_futures


def create_backend_stack(with_event_controller: bool = True):
    settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
    snapshot = TrafficSnapshotModel(settings_model=settings)
    queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
    
    view = SpyView() if with_event_controller else None
    event_controller = (
        EventController(view, snapshot, settings, queries)
        if with_event_controller
        else None
    )
    command_controller = CommandController(snapshot, snapshot, queries, settings)
    data_controller = DataController(snapshot)
    return (
        settings,
        queries,
        snapshot,
        command_controller,
        data_controller,
        event_controller,
        view,
    )


def add_basic_road_and_car(
        command_controller: CommandController, snapshot: TrafficSnapshotModel
):
    command_controller.add_road(
        name="Main",
        orientation=RoadOrientation.HORIZONTAL,
        position=0.0,
        number_of_forward_lanes=1,
        number_of_backward_lanes=0,
    )
    road = next(iter(snapshot.get_roads().values()))
    command_controller.add_car(
        name="Car1",
        assigned_road=road,
        lane_index=0,
        color="#ff0000",
        position_on_lane=10.0,
        transition=0.0,
        speed=5.0,
        length=4.0,
        acceleration=0.0,
        next_turn=None,
    )
    car = next(iter(snapshot.get_cars().values()))
    return road, car


class TestIntegrationCommandEvents(unittest.TestCase):
    def test_add_road_and_car_emits_view_updates(self):
        _, _, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        add_basic_road_and_car(command_controller, snapshot)

        self.assertEqual(len(snapshot.get_roads()), 1)
        self.assertEqual(len(snapshot.get_cars()), 1)
        self.assertEqual(len(view.added_roads), 1)
        self.assertEqual(len(view.added_cars), 1)

    def test_remove_road_removes_car_and_emits(self):
        _, _, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        road, _ = add_basic_road_and_car(command_controller, snapshot)

        command_controller.remove_road(road.uid)

        self.assertEqual(len(snapshot.get_roads()), 0)
        self.assertEqual(len(snapshot.get_cars()), 0)
        self.assertEqual(len(view.removed_roads), 1)
        self.assertEqual(len(view.removed_cars), 1)

    def test_update_road_emits_update(self):
        _, _, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        road, _ = add_basic_road_and_car(command_controller, snapshot)

        command_controller.update_road(road, name="Main Updated")

        updated_road = snapshot.get_roads()[road.uid]
        self.assertEqual(updated_road.name, "Main Updated")
        self.assertEqual(len(view.updated_roads), 1)


class TestIntegrationDataController(unittest.TestCase):
    def test_data_controller_reads_snapshot(self):
        _, _, snapshot, command_controller, data_controller, _, _ = (
            create_backend_stack(with_event_controller=False)
        )
        road, car = add_basic_road_and_car(command_controller, snapshot)

        self.assertIn(road.uid, data_controller.get_all_roads())
        self.assertIn(car.uid, data_controller.get_all_cars())

    def test_get_road_by_uid_returns_same(self):
        _, _, snapshot, command_controller, data_controller, _, _ = (
            create_backend_stack(with_event_controller=False)
        )
        road, _ = add_basic_road_and_car(command_controller, snapshot)

        self.assertEqual(data_controller.get_road_by_uid(road.uid).uid, road.uid)


class TestIntegrationPersistence(unittest.TestCase):
    def test_save_and_load_round_trip(self):
        settings, queries, snapshot, command_controller, _, _, _ = create_backend_stack(
            with_event_controller=False
        )
        _, car = add_basic_road_and_car(command_controller, snapshot)
        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="true",
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            command_controller.save_as_traffic_snapshot(tmp_path)

            fake_app = FakeAppController(settings)
            LoadTrafficSnapshot(tmp_path, fake_app).execute()

            self.assertIsNotNone(fake_app.replaced_snapshot)
            self.assertIsNotNone(fake_app.replaced_queries)
            self.assertEqual(len(fake_app.replaced_snapshot.get_roads()), 1)
            self.assertEqual(len(fake_app.replaced_snapshot.get_cars()), 1)
            self.assertEqual(len(fake_app.replaced_queries.get_queries()), 1)

            loaded_car = next(iter(fake_app.replaced_snapshot.get_cars().values()))
            self.assertEqual(loaded_car.name, car.name)

            loaded_query = next(iter(fake_app.replaced_queries.get_queries().values()))
            self.assertIn(
                loaded_query.assigned_car_uid, fake_app.replaced_snapshot.get_cars()
            )
        finally:
            os.remove(tmp_path)

    def test_deserialize_filters_queries_with_missing_car(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [],
            "cars": [],
            "queries": [
                {
                    "uid": "q1",
                    "latex": "true",
                    "should_only_evaluate_on_cars_lane": False,
                    "assigned_car_uid": "missing",
                }
            ],
        }

        PersistenceService.deserialize(payload, snapshot, snapshot, settings, queries)

        self.assertEqual(len(queries.get_queries()), 0)

    def test_deserialize_maps_assigned_car_name(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "road-1",
                    "name": "Main",
                    "orientation": "HORIZONTAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 0,
                }
            ],
            "cars": [
                {
                    "uid": "car-1",
                    "name": "CarA",
                    "road_uid": "road-1",
                    "lane_index": 0,
                    "position_on_lane": 10.0,
                    "transition": 0.0,
                    "speed": 5.0,
                    "length": 4.0,
                    "color": "#ff0000",
                    "acceleration": 0.0,
                    "next_turn": None,
                }
            ],
            "queries": [
                {
                    "uid": "q1",
                    "latex": "true",
                    "should_only_evaluate_on_cars_lane": False,
                    "assigned_car_name": "CarA",
                }
            ],
        }

        PersistenceService.deserialize(payload, snapshot, snapshot, settings, queries)

        self.assertEqual(len(queries.get_queries()), 1)
        query = next(iter(queries.get_queries().values()))
        self.assertEqual(query.assigned_car_uid, "car-1")

    def test_command_controller_load_sets_current_path(self):
        settings, queries, snapshot, command_controller, _, _, _ = create_backend_stack(
            with_event_controller=False
        )
        add_basic_road_and_car(command_controller, snapshot)
        payload = PersistenceService.serialize(snapshot, queries)

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with open(tmp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)

            fake_app = FakeAppController(settings)
            command_controller_with_app = CommandController(
                snapshot,
                snapshot,
                queries,
                settings,
                application_controller=fake_app,
            )
            command_controller_with_app.load_traffic_snapshot(tmp_path)

            self.assertEqual(
                command_controller_with_app.get_current_snapshot_path(), tmp_path
            )
            self.assertIsNotNone(fake_app.replaced_snapshot)
        finally:
            os.remove(tmp_path)


class TestIntegrationDirtyState(unittest.TestCase):
    def test_dirty_state_true_on_modify_emits_signal(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        
        fake_app = FakeAppController(settings)
        command_controller = CommandController(
            snapshot, snapshot, queries, settings, application_controller=fake_app
        )

        command_controller.add_road(
            name="Main",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=0,
        )

        self.assertEqual(
            fake_app.view_event_handler.get_on_snapshot_changed_signal().values, [True]
        )

    def test_dirty_state_false_after_save_as_emits(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        
        fake_app = FakeAppController(settings)
        command_controller = CommandController(
            snapshot, snapshot, queries, settings, application_controller=fake_app
        )

        command_controller.add_road(
            name="Main",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=0,
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            command_controller.save_as_traffic_snapshot(tmp_path)
            self.assertEqual(
                fake_app.view_event_handler.get_on_snapshot_changed_signal().values,
                [True, False, False],
            )
        finally:
            os.remove(tmp_path)


class TestIntegrationQueryEvaluation(unittest.TestCase):
    def test_true_query_holds_and_updates_view(self):
        _, queries, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        _, car = add_basic_road_and_car(command_controller, snapshot)

        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="true",
        )

        self.assertTrue(
            wait_until(
                lambda: any(q.holding for q in queries.get_queries().values()),
                timeout=1.0,
            )
        )
        query = next(iter(queries.get_queries().values()))
        self.assertTrue(query.holding)
        self.assertGreaterEqual(len(view.updated_queries), 1)

    def test_json_snapshot_load_then_query_evaluation(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "776c9689-0ea8-4721-8bf9-3ca7c8c13c45",
                    "name": "R1",
                    "orientation": "HORIZONTAL",
                    "position": -0.6616768397300579,
                    "number_of_forward_lanes": 5,
                    "number_of_backward_lanes": 5,
                }
            ],
            "cars": [
                {
                    "uid": "06d76186-68d5-47e4-a4b3-e3b85d972671",
                    "name": "a",
                    "road_uid": "776c9689-0ea8-4721-8bf9-3ca7c8c13c45",
                    "lane_index": 0,
                    "position_on_lane": -6.0,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None,
                },
                {
                    "uid": "ebf71e64-2e83-4676-92aa-fd0f03eea3ea",
                    "name": "b",
                    "road_uid": "776c9689-0ea8-4721-8bf9-3ca7c8c13c45",
                    "lane_index": 0,
                    "position_on_lane": 7,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None,
                },
                {
                    "uid": "9ff7e9b9-eaa7-40d7-a8d4-1abb44cc90b6",
                    "name": "c",
                    "road_uid": "776c9689-0ea8-4721-8bf9-3ca7c8c13c45",
                    "lane_index": 1,
                    "position_on_lane": -6.0,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None,
                },
                {
                    "uid": "86a78d09-091c-429a-b314-5fa5dafd044e",
                    "name": "d",
                    "road_uid": "776c9689-0ea8-4721-8bf9-3ca7c8c13c45",
                    "lane_index": 1,
                    "position_on_lane": 1.7715123568688913,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None,
                },
            ],
            "queries": [],
        }
        json_string = json.dumps(payload)
        data = json.loads(json_string)

        PersistenceService.deserialize(data, snapshot, snapshot, settings, queries)

        view = SpyView()
        EventController(view, snapshot, settings, queries)
        command_controller = CommandController(snapshot, snapshot, queries, settings)

        car_a = snapshot.get_car_by_name("a")
        self.assertIsNotNone(car_a)

        # validate queries
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="forall x: ((x != a) => !<re{a} and re{x}>)",
        )

        # command_controller.add_umlsl_query(
        #     assigned_car_uid=car_a.uid,
        #     should_only_evaluate_on_cars_lane=False,
        #     latex="a != a",
        # )
        #
        def is_holding():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("forall x: ((x != a) => !<re{a} and re{x}>)")
            return target is not None and target.holding

        self.assertTrue(wait_for_evaluations(queries))
        self.assertTrue(is_holding())
        queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
        self.assertTrue(
            queries_by_latex["forall x: ((x != a) => !<re{a} and re{x}>)"].holding
        )

    def test_complex_queries_with_json(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "05924228-6663-41bf-be34-a6a05b781905",
                    "name": "R1",
                    "orientation": "HORIZONTAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "b3a40a27-bf70-40fa-9d74-f241c294b23b",
                    "name": "R3",
                    "orientation": "HORIZONTAL",
                    "position": 8.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "1ceb6d9e-d904-4374-85e9-635a872627a7",
                    "name": "R2",
                    "orientation": "VERTICAL",
                    "position": 4.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "6eef3f21-0458-4ff2-aebe-92dc79515af4",
                    "name": "R4",
                    "orientation": "VERTICAL",
                    "position": 12.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                }
            ],
            "cars": [
                {
                    "uid": "a3d7dc53-f686-4c9d-a72e-1a761895c3bd",
                    "name": "a",
                    "road_uid": "05924228-6663-41bf-be34-a6a05b781905",
                    "lane_index": 0,
                    "position_on_lane": -2.0,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                },
                {
                    "uid": "90fd5982-dfb5-4804-89ff-f246fed5ce9e",
                    "name": "b",
                    "road_uid": "05924228-6663-41bf-be34-a6a05b781905",
                    "lane_index": 0,
                    "position_on_lane": 0.9894008691374196,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                }
            ],
            "queries": [],
        }
        json_string = json.dumps(payload)
        data = json.loads(json_string)

        PersistenceService.deserialize(data, snapshot, snapshot, settings, queries)

        view = SpyView()
        EventController(view, snapshot, settings, queries)
        command_controller = CommandController(snapshot, snapshot, queries, settings)

        car_a = snapshot.get_car_by_name("a")
        self.assertIsNotNone(car_a)

        # validate queries
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<hchop{re{a}}{l > 2 and free and !<cs>}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{b}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{b}>",
        )

        def is_holding_query_1():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<hchop{re{a}}{l > 2 and free and !<cs>}>")
            return target is not None and target.holding

        def is_holding_query_2():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{b}>")
            return target is not None and target.holding

        def is_holding_query_3():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{b}>")

            return target is not None and target.holding

        self.assertTrue(wait_for_evaluations(queries))
        self.assertFalse(is_holding_query_1())
        self.assertTrue(is_holding_query_2())
        self.assertTrue(is_holding_query_3())

    def test_collision_queries_with_json(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "name": "1",
                    "orientation": "HORIZONTAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "name": "2",
                    "orientation": "VERTICAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                }
            ],
            "cars": [
                {
                    "uid": "ccd22c5d-1e7b-43e1-890d-2b7b7c00734d",
                    "name": "a",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": 0,
                    "position_on_lane": -3.1524314488274943,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": {
                        "direction": "LEFT",
                        "target_lane": {
                            "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                            "lane_index": 0
                        }
                    }
                },
                {
                    "uid": "92498266-6594-4fa5-8f46-e58779e410ff",
                    "name": "b",
                    "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "lane_index": 0,
                    "position_on_lane": 2.818842512724892,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                },
                {
                    "uid": "b9d6a69a-f065-412c-af74-1ef215334e4f",
                    "name": "c",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": 0,
                    "position_on_lane": 1.4234117933103105,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                },
                {
                    "uid": "d941ba14-2a6b-4926-a93b-8da1513eb6f8",
                    "name": "d",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": -1,
                    "position_on_lane": 3.0,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                }
            ],
            "queries": []
        }
        json_string = json.dumps(payload)
        data = json.loads(json_string)

        PersistenceService.deserialize(data, snapshot, snapshot, settings, queries)

        view = SpyView()
        EventController(view, snapshot, settings, queries)
        command_controller = CommandController(snapshot, snapshot, queries, settings)

        car_a = snapshot.get_car_by_name("a")
        self.assertIsNotNone(car_a)

        # validate queries
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{b}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{c}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{d}>",
        )

        def is_holding_query_1():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{b}>")
            return target is not None and target.holding

        def is_holding_query_2():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{c}>")
            return target is not None and target.holding

        def is_holding_query_3():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{d}>")

            return target is not None and target.holding

        self.assertTrue(wait_for_evaluations(queries))
        self.assertTrue(is_holding_query_1())
        # 'a' turns left onto road 2 at the crossing, so its reserved space runs
        # road 1 -> crossing -> road 2 and never reaches the stretch of road 1
        # beyond the crossing where 'c' stands. The two reservations cannot meet.
        self.assertFalse(is_holding_query_2())
        self.assertTrue(is_holding_query_3())

    def test_view_queries_with_json(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "name": "1",
                    "orientation": "HORIZONTAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "name": "2",
                    "orientation": "VERTICAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                }
            ],
            "cars": [
                {
                    "uid": "ccd22c5d-1e7b-43e1-890d-2b7b7c00734d",
                    "name": "a",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": 0,
                    "position_on_lane": -4.930245086120705,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": {
                        "direction": "LEFT",
                        "target_lane": {
                            "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                            "lane_index": 0
                        }
                    }
                },
                {
                    "uid": "92498266-6594-4fa5-8f46-e58779e410ff",
                    "name": "b",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": -1,
                    "position_on_lane": -6.807123091134452,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                },
                {
                    "uid": "de845750-a341-4410-a415-c4e36cd6ce90",
                    "name": "c",
                    "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "lane_index": 0,
                    "position_on_lane": 5.0,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                },
                {
                    "uid": "930d4a9d-b5b7-45a4-9eab-008eeec3c16e",
                    "name": "d",
                    "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "lane_index": -1,
                    "position_on_lane": -3.0332390709696364,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": None
                }
            ],
            "queries": []
        }
        json_string = json.dumps(payload)
        data = json.loads(json_string)

        PersistenceService.deserialize(data, snapshot, snapshot, settings, queries)

        view = SpyView()
        EventController(view, snapshot, settings, queries)
        command_controller = CommandController(snapshot, snapshot, queries, settings)

        car_a = snapshot.get_car_by_name("a")
        self.assertIsNotNone(car_a)

        # validate queries
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{b}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{c}>",
        )
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<re{a} and re{d}>",
        )

        def is_holding_query_1():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{b}>")
            return target is not None and target.holding

        def is_holding_query_2():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{c}>")
            return target is not None and target.holding

        def is_holding_query_3():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<re{a} and re{d}>")

            return target is not None and target.holding

        self.assertTrue(wait_for_evaluations(queries))
        # 'b' shares road 1 with 'a' on the parallel backward lane, so its
        # reservation is visible somewhere in a's view.
        self.assertTrue(is_holding_query_1())
        # 'c' sits far up road 2; a's reservation reaches only just past the
        # crossing, so the two never meet.
        self.assertFalse(is_holding_query_2())
        # 'd' drives down road 2's backward lane and is already below the
        # crossing, i.e. moving away from a's path rather than into it.
        self.assertFalse(is_holding_query_3())

    def test_complex_h_chop_queries_with_json(self):
        settings = SettingsModel(braking_acceleration=8.0, max_speed=15.0)
        snapshot = TrafficSnapshotModel(settings_model=settings)
        queries = UMLSLQueriesModel(traffic_snapshot=snapshot)
        

        payload = {
            "meta": {"version": PersistenceService.VERSION},
            "roads": [
                {
                    "uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "name": "1",
                    "orientation": "HORIZONTAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                },
                {
                    "uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                    "name": "2",
                    "orientation": "VERTICAL",
                    "position": 0.0,
                    "number_of_forward_lanes": 1,
                    "number_of_backward_lanes": 1
                }
            ],
            "cars": [
                {
                    "uid": "ccd22c5d-1e7b-43e1-890d-2b7b7c00734d",
                    "name": "a",
                    "road_uid": "7c66b458-6ffd-43df-a19c-251add9c973b",
                    "lane_index": 0,
                    "position_on_lane": -4.930245086120705,
                    "transition": 0.0,
                    "speed": 10.0,
                    "length": 1,
                    "color": "lightblue",
                    "acceleration": 1.0,
                    "next_turn": {
                        "direction": "LEFT",
                        "target_lane": {
                            "road_uid": "8c38244a-f310-4a52-9660-c72d17c089a2",
                            "lane_index": 0
                        }
                    }
                }
            ],
            "queries": []
        }
        json_string = json.dumps(payload)
        data = json.loads(json_string)

        PersistenceService.deserialize(data, snapshot, snapshot, settings, queries)

        view = SpyView()
        EventController(view, snapshot, settings, queries)
        command_controller = CommandController(snapshot, snapshot, queries, settings)

        car_a = snapshot.get_car_by_name("a")
        self.assertIsNotNone(car_a)

        # validate queries
        command_controller.add_umlsl_query(
            assigned_car_uid=car_a.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="<hchop{re{a}}{l>2 and free and !<cs>}>",
        )

        def is_holding_query_1():
            queries_by_latex = {q.latex: q for q in queries.get_queries().values()}
            target = queries_by_latex.get("<hchop{re{a}}{l>2 and free and !<cs>}>")
            return target is not None and target.holding

        self.assertTrue(wait_for_evaluations(queries))
        self.assertTrue(is_holding_query_1())

    def test_parser_evaluates_true_and_negation(self):
        _, _, snapshot, command_controller, _, _, _ = create_backend_stack(
            with_event_controller=False
        )
        _, car = add_basic_road_and_car(command_controller, snapshot)

        evaluator = UMLSLEvaluator(snapshot)
        parsed_true = evaluator.parse_ast("true", car)
        self.assertTrue(parsed_true.evaluate(evaluate_ego_lane_only=False))

        parsed_neg_true = evaluator.parse_ast("neg true", car)
        self.assertFalse(parsed_neg_true.evaluate(evaluate_ego_lane_only=False))

    def test_parser_evaluates_basic_logical_conditions(self):
        _, _, snapshot, command_controller, _, _, _ = create_backend_stack(
            with_event_controller=False
        )
        _, car = add_basic_road_and_car(command_controller, snapshot)

        evaluator = UMLSLEvaluator(snapshot)
        parsed_true = evaluator.parse_ast("!true", car)
        self.assertFalse(parsed_true.evaluate(evaluate_ego_lane_only=False))

        parsed_neg_true = evaluator.parse_ast("(true or !true)", car)
        self.assertTrue(parsed_neg_true.evaluate(evaluate_ego_lane_only=False))

        parsed_neg_true = evaluator.parse_ast("(true => !true)", car)
        self.assertFalse(parsed_neg_true.evaluate(evaluate_ego_lane_only=False))

        parsed_neg_true = evaluator.parse_ast("(!true => true)", car)
        self.assertTrue(parsed_neg_true.evaluate(evaluate_ego_lane_only=False))

        parsed_neg_true = evaluator.parse_ast("!(true and !true)", car)
        self.assertTrue(parsed_neg_true.evaluate(evaluate_ego_lane_only=False))

    def test_query_removed_when_assigned_car_removed(self):
        _, queries, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        road, car = add_basic_road_and_car(command_controller, snapshot)

        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="true",
        )

        self.assertTrue(
            wait_until(lambda: len(queries.get_queries()) == 1, timeout=1.0)
        )
        command_controller.remove_road(road.uid)
        self.assertTrue(
            wait_until(lambda: len(queries.get_queries()) == 0, timeout=1.0)
        )
        self.assertTrue(wait_until(lambda: len(view.removed_queries) == 1, timeout=1.0))

        self.assertEqual(len(queries.get_queries()), 0)
        self.assertEqual(len(view.removed_queries), 1)

    def test_query_removed_when_car_removed(self):
        _, queries, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )
        _, car = add_basic_road_and_car(command_controller, snapshot)

        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="true",
        )

        self.assertTrue(
            wait_until(lambda: len(queries.get_queries()) == 1, timeout=1.0)
        )
        command_controller.remove_car(car.uid)
        self.assertTrue(
            wait_until(lambda: len(queries.get_queries()) == 0, timeout=1.0)
        )
        self.assertTrue(wait_until(lambda: len(view.removed_queries) == 1, timeout=1.0))

        self.assertEqual(len(queries.get_queries()), 0)
        self.assertEqual(len(view.removed_queries), 1)

    def test_crossing_segment_node_and_claim_node(self):
        settings, queries, snapshot, command_controller, _, _, view = create_backend_stack(
            with_event_controller=True
        )

        # Add two roads that cross
        command_controller.add_road(
            name="RoadH",
            orientation=RoadOrientation.HORIZONTAL,
            position=0.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=0,
        )
        command_controller.add_road(
            name="RoadV",
            orientation=RoadOrientation.VERTICAL,
            position=0.0,
            number_of_forward_lanes=1,
            number_of_backward_lanes=0,
        )

        road_h = next(r for r in snapshot.get_roads().values() if r.name == "RoadH")
        road_v = next(r for r in snapshot.get_roads().values() if r.name == "RoadV")

        # Add car at crossing
        command_controller.add_car(
            name="Car1",
            assigned_road=road_h,
            lane_index=0,
            color="#ff0000",
            position_on_lane=0.0,  # at crossing
            transition=0.0,
            speed=0.0,
            length=4.0,
            acceleration=0.0,
            next_turn=None,
        )

        car = next(iter(snapshot.get_cars().values()))

        # Query for crossing segment node
        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=True,
            latex="cs",
        )

        # Wait for queries to be added
        self.assertTrue(
            wait_until(
                lambda: len(queries.get_queries()) == 1,
                timeout=5.0,
            )
        )

        query_cs = next(q for q in queries.get_queries().values() if q.latex == "cs")
        self.assertFalse(query_cs.holding)  # Horizon includes lane segments

        # Query for claim node - should be false since no claims
        command_controller.add_umlsl_query(
            assigned_car_uid=car.uid,
            should_only_evaluate_on_cars_lane=False,
            latex="cl\\left(Car1\\right)",
        )

        # Wait for second query
        self.assertTrue(
            wait_until(
                lambda: len(queries.get_queries()) == 2,
                timeout=5.0,
            )
        )

        query_cl = next(q for q in queries.get_queries().values() if "cl" in q.latex)
        self.assertFalse(query_cl.holding)  # No claims


if __name__ == "__main__":
    unittest.main()
