from PySide6.QtCore import Signal, SignalInstance

from umlsl_edit.controllers.view_event_contract import ViewEventHandler
from umlsl_edit.model.entities.car import Car
from umlsl_edit.model.entities.road import Road
from umlsl_edit.model.entities.umlsl_query import UMLSLQuery
from umlsl_edit.view.view_models import ViewModels


class ViewEventHandlerImplementation(ViewEventHandler):
    selection_changed = Signal(str)
    snapshot_changed = Signal(bool)
    toggle_coordinate_system_signal = Signal(bool)
    toggle_grid_signal = Signal(bool)
    toggle_safety_distance_signal = Signal(bool)
    show_snackbar_message = Signal(str, int)

    def get_on_selection_changed_signal(self) -> "SignalInstance":
        return self.selection_changed

    def get_on_snapshot_changed_signal(self) -> "SignalInstance":
        return self.snapshot_changed

    def get_on_toggle_coordinate_system_signal(self) -> "SignalInstance":
        return self.toggle_coordinate_system_signal

    def get_on_toggle_grid_signal(self) -> "SignalInstance":
        return self.toggle_grid_signal

    def get_on_toggle_safety_distance_signal(self) -> "SignalInstance":
        return self.toggle_safety_distance_signal

    def get_on_show_snackbar_message_signal(self) -> "SignalInstance":
        return self.show_snackbar_message

    def __init__(self, view_models: ViewModels) -> None:
        super().__init__()
        self.view_models: ViewModels = view_models
        self.current_selected_uid = ""
        self.should_render_coordinate_system = True
        self.should_render_grid = True
        self.should_render_safety_distance = True

    def _select_entity(self, uid: str) -> None:
        if uid == self.current_selected_uid:
            return
        self.current_selected_uid = uid
        self.selection_changed.emit(self.current_selected_uid)

    def add_car_view(self, car: Car) -> None:
        self.view_models.car_list_model.add_entity(car)
        self._select_entity(car.uid)

    def remove_car_view(self, car: Car) -> None:
        self.view_models.car_list_model.remove_entity(car)

    def update_car_view(self, car: Car) -> None:
        self.view_models.car_list_model.update_entity(car)

    def add_road_view(self, road: Road) -> None:
        self.view_models.road_list_model.add_entity(road)
        self._select_entity(road.uid)

    def remove_road_view(self, road: Road) -> None:
        self.view_models.road_list_model.remove_entity(road)

    def update_road_view(self, road: Road) -> None:
        self.view_models.road_list_model.update_entity(road)

    def add_query_view(self, query: UMLSLQuery) -> None:
        self.view_models.query_list_model.add_entity(query)
        self._select_entity(query.uid)

    def remove_query_view(self, query: UMLSLQuery) -> None:
        self.view_models.query_list_model.remove_entity(query)

    def update_query_view(self, query: UMLSLQuery) -> None:
        self.view_models.query_list_model.update_entity(query)
        self.view_models.query_list_model.set_query_loading(query.uid, False)

    def loading_query_view(self, query_payload: UMLSLQuery | dict) -> None:
        if isinstance(query_payload, dict):
            query_obj = query_payload.get("query")
            is_loading = bool(query_payload.get("is_loading"))
        else:
            query_obj = query_payload
            is_loading = True

        if query_obj is None:
            return

        self.view_models.query_list_model.set_query_loading(query_obj.uid, is_loading)

    def revalidation_finished(self) -> None:
        # self.show_snackbar_message.emit("All queries evaluated", 3000)
        pass

    def revalidation_started(self) -> None:
        self.view_models.query_list_model.set_all_queries_loading()

    def on_snapshot_reloaded(self, snapshot, queries=None) -> None:
        if queries is None and isinstance(snapshot, dict):
            snapshot_model = snapshot.get("snapshot")
            queries_model = snapshot.get("queries")
        else:
            snapshot_model = snapshot
            queries_model = queries

        if snapshot_model is None or queries_model is None:
            return

        self.view_models.car_list_model.clear_all()
        self.view_models.road_list_model.clear_all()
        self.view_models.query_list_model.clear_all()

        for road in snapshot_model.get_roads().values():
            self.view_models.road_list_model.add_entity(road)
        for car in snapshot_model.get_cars().values():
            self.view_models.car_list_model.add_entity(car)
        for query in queries_model.get_queries().values():
            self.view_models.query_list_model.add_entity(query)

        self.current_selected_uid = ""
        self.selection_changed.emit(self.current_selected_uid)

    def set_coordinate_system(self, render_coordinate_system: bool) -> None:
        self.should_render_coordinate_system = render_coordinate_system
        self.toggle_coordinate_system_signal.emit(render_coordinate_system)

    def set_grid(self, render_grid: bool) -> None:
        self.should_render_grid = render_grid
        self.toggle_grid_signal.emit(render_grid)

    def set_safety_distance(self, render_safety_distance: bool) -> None:
        self.should_render_safety_distance = render_safety_distance
        self.toggle_safety_distance_signal.emit(render_safety_distance)

    def get_current_selected_uid(self) -> str:
        return self.current_selected_uid

    def entity_selected_view(self, uid: str) -> None:
        if uid != self.current_selected_uid:
            self.current_selected_uid = uid
        else:
            self.current_selected_uid = ""

        self.selection_changed.emit(self.current_selected_uid)
