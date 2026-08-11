"""
Settings dialog for the UMLSL Traffic Editor.

Provides a dialog window for configuring application settings.
"""

from PySide6.QtWidgets import QDialog

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.view.widgets.compiled_widgets.ui_settings_dialog import (
    Ui_Settings_Dialog,
)


class SettingsDialog(QDialog, Ui_Settings_Dialog):
    """
    Dialog for configuring application settings.

    This dialog provides a user interface for modifying application preferences
    and configuration options. It inherits from both QDialog for dialog behavior
    and Ui_Settings_Dialog for the auto-generated UI layout.

    Attributes:
        Inherits all attributes from QDialog and Ui_Settings_Dialog.
    """

    def __init__(self, application_controller: "ApplicationController", parent=None):
        """
        Initialize the settings dialog.

        Args:
            application_controller: The application controller for view and settings updates.
            parent: The parent widget for this dialog. Defaults to None.
        """
        super().__init__(parent)
        self._application_controller = application_controller
        self.setupUi(self)

        self._coordinate_system_checkbox = self.c_coordinate_system
        self._grid_checkbox = self.c_grid
        self._safety_distance_checkbox = self.c_savty_space
        self._braking_spinbox = self.s_braking
        self._max_speed_spinbox = self.s_accerleration

        self._coordinate_system_checkbox.clicked.connect(self._on_toggle_coordinate_system)
        self._coordinate_system_checkbox.setChecked(
            self._application_controller.view_event_handler.should_render_coordinate_system
        )

        self._grid_checkbox.clicked.connect(self._on_toggle_grid)
        self._grid_checkbox.setChecked(self._application_controller.view_event_handler.should_render_grid)

        self._safety_distance_checkbox.clicked.connect(self._on_toggle_safety_distance)
        self._safety_distance_checkbox.setChecked(
            self._application_controller.view_event_handler.should_render_safety_distance
        )

        self._braking_spinbox.setValue(
            self._application_controller.command_controller.settings_model.braking_acceleration
        )
        self._braking_spinbox.valueChanged.connect(self._on_braking_changed)
        self._max_speed_spinbox.setValue(
            self._application_controller.command_controller.settings_model.max_speed
        )
        self._max_speed_spinbox.valueChanged.connect(self._on_max_speed_changed)

        # TODO: Enable this once the safety-distance overlay is implemented.
        self.l_reserved.hide()
        self._safety_distance_checkbox.hide()

    def _on_braking_changed(self) -> None:
        self._application_controller.command_controller.settings_model.set_braking_acceleration(
            self._braking_spinbox.value()
        )

    def _on_max_speed_changed(self) -> None:
        self._application_controller.command_controller.settings_model.set_max_speed(
            self._max_speed_spinbox.value()
        )

    def _on_toggle_coordinate_system(self) -> None:
        """Toggle coordinate system overlay rendering."""
        is_checked = self._coordinate_system_checkbox.isChecked()
        self._application_controller.view_event_handler.set_coordinate_system(is_checked)

    def _on_toggle_grid(self) -> None:
        """Toggle grid overlay rendering."""
        is_checked = self._grid_checkbox.isChecked()
        self._application_controller.view_event_handler.set_grid(is_checked)

    def _on_toggle_safety_distance(self) -> None:
        """Toggle safety distance overlay rendering."""
        is_checked = self._safety_distance_checkbox.isChecked()
        self._application_controller.view_event_handler.set_safety_distance(is_checked)
