"""
Main window module for the UMLSL Traffic Editor.

This module contains the MainWindow class, which serves as the primary
application window and coordinates all UI components.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QSpinBox,
    QTextEdit,
)

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.view.ui.global_controls import GlobalControls
from umlsl_edit.view.ui.lists.edit_dialogs.confirm_deletion_dialog import (
    ConfirmDeletionDialog,
)
from umlsl_edit.view.ui.lists.sidebar_controller import SidebarController
from umlsl_edit.view.ui.lists.snackbar import GreenSnackbar
from umlsl_edit.view.ui.traffic_canvas.canvas_buttons import CanvasButtons
from umlsl_edit.view.ui.traffic_canvas.traffic_scene import TrafficScene
from umlsl_edit.view.ui.traffic_canvas.traffic_view import TrafficView
from umlsl_edit.view.widgets.compiled_widgets.ui_main import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Primary application window for the UMLSL Traffic Editor.

    This class integrates all major UI components including the traffic canvas,
    sidebar controls, and global application controls. It inherits from both
    QMainWindow for Qt functionality and Ui_MainWindow for the compiled UI layout.

    Attributes:
        traffic_scene: The graphics scene containing all traffic entities.
        trafficView: The graphics view for rendering and interacting with the scene.
        canvas_buttons: Controller for zoom and overlay buttons on the canvas.
        sidebar_controller: Controller for the sidebar entity lists.
        global_controls: Controller for menu actions (save, open, settings).
    """

    def __init__(self, application_controller: ApplicationController) -> None:
        """
        Initialize the main window with all UI components.

        Args:
            application_controller: The central controller managing application
                state and coordinating between model, view, and commands.
        """
        super().__init__()
        self._application_controller = application_controller
        self.setupUi(self)

        self._setup_traffic_canvas()
        self._setup_controllers()
        self._setup_shortcuts()

        self.snackbar = GreenSnackbar(self.sidebar)

        self._application_controller.view_event_handler.get_on_snapshot_changed_signal().connect(
            self._on_snapshot_changed
        )
        self._application_controller.view_event_handler.get_on_show_snackbar_message_signal().connect(
            self.snackbar.show_message
        )

        self.update_main_window_title()

    def _setup_traffic_canvas(self) -> None:
        """
        Initialize and configure the traffic canvas components.

        Replaces the placeholder graphics view from the UI file with the
        custom TrafficView and TrafficScene.
        """
        self.traffic_scene = TrafficScene(self._application_controller)
        self.trafficView = TrafficView(scene=self.traffic_scene, application_controller=self._application_controller)

        layout = self.graphicsView.parentWidget().layout()
        layout.replaceWidget(self.graphicsView, self.trafficView)
        self.graphicsView.deleteLater()

    def _setup_controllers(self) -> None:
        """
        Initialize UI controllers for various window components.
        """
        self.canvas_buttons = CanvasButtons(self)
        self.sidebar_controller = SidebarController(self, self._application_controller)
        self.global_controls = GlobalControls(self, self._application_controller)

    def _setup_shortcuts(self) -> None:
        self._shortcuts = [
            self._create_shortcut("C", self.sidebar_controller.open_add_car_dialog),
            self._create_shortcut("R", self.sidebar_controller.open_add_road_dialog),
            self._create_shortcut("Q", self.sidebar_controller.open_add_query_dialog),
            self._create_shortcut("E", self._handle_edit_shortcut),
            self._create_shortcut("Backspace", self._handle_delete_shortcut),
        ]

    def _create_shortcut(self, key: str, handler) -> QShortcut:
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.setContext(Qt.WindowShortcut)
        shortcut.activated.connect(lambda: self._run_shortcut_if_allowed(handler))
        return shortcut

    def _run_shortcut_if_allowed(self, handler) -> None:
        focus = self.focusWidget()
        if isinstance(
                focus,
                (
                        QLineEdit,
                        QTextEdit,
                        QPlainTextEdit,
                        QSpinBox,
                        QDoubleSpinBox,
                        QComboBox,
                ),
        ):
            return
        handler()

    def _handle_edit_shortcut(self) -> None:
        if not self._has_selected_entity():
            return
        self.sidebar_controller.open_edit_selected_entity()

    def _handle_delete_shortcut(self) -> None:
        if not self._has_selected_entity():
            return
        self.sidebar_controller.delete_selected_entity()

    def _has_selected_entity(self) -> bool:
        return bool(self._application_controller.view_event_handler.get_current_selected_uid())

    def _on_snapshot_changed(self, _changed: bool) -> None:
        self.update_main_window_title()

    def closeEvent(self, event) -> None:
        if self._application_controller.command_controller.get_data_changed_since_last_save():
            confirm = ConfirmDeletionDialog(
                "You have unsaved changes.\nDiscard them and close?",
                self,
                title="Unsaved Changes",
                confirm_text="Discard changes",
                cancel_text="Keep editing",
            ).exec()
            if confirm != QDialog.DialogCode.Accepted:
                event.ignore()
                return

        event.accept()

    def update_main_window_title(self) -> None:
        """Update the main window title based on the current snapshot path."""
        snapshot_path = self._application_controller.command_controller.get_current_snapshot_path()
        if snapshot_path:
            self.setWindowTitle(f"UMLSL-Edit - {snapshot_path}" + (
                "*" if self._application_controller.command_controller.get_data_changed_since_last_save() else ""))
        else:
            self.setWindowTitle("UMLSL-Edit - Untitled" + (
                "*" if self._application_controller.command_controller.get_data_changed_since_last_save() else ""))
