"""
Sidebar controller for the UMLSL Traffic Editor.

Manages the sidebar UI including entity lists (roads, cars, queries) and
their associated QML views and add buttons.
"""

import os

from PySide6.QtCore import QObject, Qt, QTimer, QUrl
from PySide6.QtWidgets import QDialog

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.model.entities.entity import Entity
from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog
from umlsl_edit.view.ui.lists.deletion_checks import (
    get_car_deletion_block_reason,
    get_road_deletion_block_reason,
)
from umlsl_edit.view.ui.lists.edit_dialogs.confirm_deletion_dialog import (
    ConfirmDeletionDialog,
)
from umlsl_edit.view.ui.lists.edit_dialogs.edit_car_dialog import (
    EditCarDialog,
)
from umlsl_edit.view.ui.lists.edit_dialogs.edit_query_dialog import (
    EditQueryDialog,
)
from umlsl_edit.view.ui.lists.edit_dialogs.edit_road_dialog import (
    EditRoadDialog,
)
from umlsl_edit.view.ui.lists.models.latex_image_provider import (
    LatexImageProvider,
)
from umlsl_edit.view.widgets.compiled_widgets.ui_main import Ui_MainWindow


class SidebarController(QObject):
    """
    Controller for the sidebar panel containing entity lists.

    Manages the QML-based list views for roads, cars, and queries, and handles
    the add buttons for creating new entities. Each list is backed by a model
    from the view event handler.

    Attributes:
        _view_models: Collection of view models for entity lists.
        _application_controller: Reference to the main application controller.
        _window: Reference to the main application window.
    """

    def __init__(
            self,
            main_window: Ui_MainWindow,
            application_controller: ApplicationController,
    ) -> None:
        """
        Initialize the sidebar controller.

        Args:
            main_window: The main application window containing sidebar widgets.
            application_controller: The central controller for coordinating
                model-view interactions.
        """
        super().__init__(main_window)

        self._view_models = application_controller.view_event_handler.view_models
        self._application_controller = application_controller
        self._window = main_window

        self._road_quick_widget = self._window.q_roads
        self._car_quick_widget = self._window.q_cars
        self._query_quick_widget = self._window.q_queries

        self._add_road_button = self._window.b_add_road
        self._add_car_button = self._window.b_add_car
        self._add_query_button = self._window.b_add_query

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure button connections and initialize QML list views."""
        self._connect_add_buttons()
        self._connect_edit_signals()
        self._setup_quick_widgets()

    def _connect_add_buttons(self) -> None:
        """Connect add buttons to their respective dialog handlers."""
        self._add_road_button.clicked.connect(self.open_add_road_dialog)
        self._add_car_button.clicked.connect(self.open_add_car_dialog)
        self._add_query_button.clicked.connect(self.open_add_query_dialog)

    def _connect_edit_signals(self) -> None:
        """Connect model edit_requested signals to dialog handlers."""
        self._view_models.road_list_model.edit_requested.connect(
            lambda row: self._open_edit_dialog(
                EditRoadDialog, self._view_models.road_list_model.get_entity_at(row)
            )
        )
        self._view_models.car_list_model.edit_requested.connect(
            lambda row: self._open_edit_dialog(
                EditCarDialog, self._view_models.car_list_model.get_entity_at(row)
            )
        )
        self._view_models.query_list_model.edit_requested.connect(
            lambda row: self._open_edit_dialog(
                EditQueryDialog, self._view_models.query_list_model.get_entity_at(row)
            )
        )

    def _setup_quick_widgets(self) -> None:
        """Initialize all QML Quick Widgets with their models and QML files."""
        qml_folder = self._get_qml_folder_path()

        self._configure_quick_widget(
            self._road_quick_widget,
            self._view_models.road_list_model,
            os.path.join(qml_folder, "RoadListView.qml"),
        )
        self._configure_quick_widget(
            self._car_quick_widget,
            self._view_models.car_list_model,
            os.path.join(qml_folder, "CarListView.qml"),
        )
        # Register the LaTeX image provider before loading the QML
        self._latex_image_provider = LatexImageProvider()
        self._query_quick_widget.engine().addImageProvider(
            "latex", self._latex_image_provider
        )

        self._configure_quick_widget(
            self._query_quick_widget,
            self._view_models.query_list_model,
            os.path.join(qml_folder, "QueryListView.qml"),
        )

    def _get_qml_folder_path(self) -> str:
        """
        Get the absolute path to the QML folder.

        Returns:
            Absolute path to the qml subfolder relative to this module.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "qml")

    def _configure_quick_widget(
            self,
            quick_widget,
            model,
            qml_file_path: str,
    ) -> None:
        """
        Configure a QML Quick Widget with the specified model and QML file.

        Sets up transparency, resize behavior, and binds the data model
        to the QML context.

        Args:
            quick_widget: The QQuickWidget to configure.
            model: The data model to expose to QML.
            qml_file_path: Path to the QML file defining the view.
        """
        quick_widget.setClearColor(Qt.transparent)
        quick_widget.setAttribute(Qt.WA_TranslucentBackground)
        quick_widget.setAttribute(Qt.WA_AlwaysStackOnTop)
        quick_widget.setResizeMode(quick_widget.ResizeMode.SizeRootObjectToView)

        quick_widget.rootContext().setContextProperty("data_model", model)
        quick_widget.setSource(QUrl.fromLocalFile(qml_file_path))

    def open_add_car_dialog(self) -> None:
        self._open_edit_dialog(EditCarDialog, None)

    def open_add_road_dialog(self) -> None:
        self._open_edit_dialog(EditRoadDialog, None)

    def open_add_query_dialog(self) -> None:
        self._open_edit_dialog(EditQueryDialog, None)

    def open_edit_selected_entity(self) -> None:
        selected = self._get_selected_entity()
        if selected is None:
            return

        entity, entity_type = selected
        if entity_type == "car":
            self._open_edit_dialog(EditCarDialog, entity)
        elif entity_type == "road":
            self._open_edit_dialog(EditRoadDialog, entity)
        elif entity_type == "query":
            self._open_edit_dialog(EditQueryDialog, entity)

    def delete_selected_entity(self) -> None:
        selected = self._get_selected_entity()
        if selected is None:
            return

        entity, entity_type = selected
        if entity_type == "car":
            block_reason = get_car_deletion_block_reason(self._application_controller, entity)
            if block_reason:
                WarningDialog("Cannot delete car", block_reason, self._window).exec()
                return
            label = f"car '{entity.name}'"
            delete_action = lambda: self._application_controller.command_controller.remove_car(entity.uid)
        elif entity_type == "road":
            block_reason = get_road_deletion_block_reason(self._application_controller, entity)
            if block_reason:
                WarningDialog("Cannot delete road", block_reason, self._window).exec()
                return
            label = f"road '{entity.name}'"
            delete_action = lambda: self._application_controller.command_controller.remove_road(entity.uid)
        else:
            if self._view_models.query_list_model.is_query_loading(entity.uid):
                WarningDialog(
                    "Cannot delete query",
                    "This query is still loading. Please wait until it finishes.",
                    self._window,
                ).exec()
                return
            label = "this query"
            delete_action = lambda: self._application_controller.command_controller.remove_umlsl_query(entity.uid)

        dialog_result = ConfirmDeletionDialog(
            f"Delete {label}?",
            self._window,
            title="Confirm deletion",
            confirm_text="Delete",
            cancel_text="Cancel",
        ).exec()

        if dialog_result == QDialog.DialogCode.Accepted:
            QTimer.singleShot(0, delete_action)
            if entity_type == "car":
                self._window.snackbar.show_message(f"Car '{entity.name}' deleted successfully.")
            elif entity_type == "road":
                self._window.snackbar.show_message(f"Road '{entity.name}' deleted successfully.")
            else:
                self._window.snackbar.show_message("Query deleted successfully.")

    def _get_selected_entity(self) -> tuple[Entity, str] | None:
        selected_uid = self._application_controller.view_event_handler.get_current_selected_uid()
        if not selected_uid:
            return None

        cars = self._application_controller.data_controller.get_all_cars()
        if selected_uid in cars:
            return cars[selected_uid], "car"

        roads = self._application_controller.data_controller.get_all_roads()
        if selected_uid in roads:
            return roads[selected_uid], "road"

        queries = self._application_controller.command_controller.umlsl_queries_model.get_queries()
        if selected_uid in queries:
            return queries[selected_uid], "query"

        return None

    def _open_edit_dialog(self, dialog_class, entity: Entity | None) -> None:
        """
        Open an edit dialog for an entity.

        Args:
            dialog_class: The dialog class to instantiate (e.g., EditRoadDialog).
            entity: The entity to edit, or None for create mode.
        """

        dialog = dialog_class(
            entity,
            parent=self._window,
            application_controller=self._application_controller,
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose)
        dialog.exec()
