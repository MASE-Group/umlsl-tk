from typing import TYPE_CHECKING

from umlsl_edit.view.ui.lists.models.car_list_model import CarModel
from umlsl_edit.view.ui.lists.models.query_list_model import QueryListModel
from umlsl_edit.view.ui.lists.models.road_list_model import RoadListModel

if TYPE_CHECKING:
    from umlsl_edit.controllers import ApplicationController
    from umlsl_edit.controllers.view_event_contract import ViewEventHandler


class ViewModels:
    def __init__(self, application_controller: "ApplicationController") -> None:
        self.car_list_model = CarModel(application_controller=application_controller)
        self.road_list_model = RoadListModel(application_controller=application_controller)
        self.query_list_model = QueryListModel(application_controller=application_controller)

    def connect_signals(self, view_event_handler: "ViewEventHandler") -> None:
        self.car_list_model.connect_signal(view_event_handler)
        self.road_list_model.connect_signal(view_event_handler)
        self.query_list_model.connect_signal(view_event_handler)
