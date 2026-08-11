"""
Global controls for the UMLSL Traffic Editor.

Handles global UI actions such as save, open, and settings from the main menu bar.
"""
import platform

from PySide6.QtCore import QObject
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QFileDialog

from umlsl_edit.commands.command import CommandValidationError
from umlsl_edit.controllers import ApplicationController
from umlsl_edit.model.errors.errors import BaseError
from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog
from umlsl_edit.view.ui.lists.edit_dialogs.confirm_deletion_dialog import (
    ConfirmDeletionDialog,
)
from umlsl_edit.view.ui.settings.settings_dialog import SettingsDialog
from umlsl_edit.view.widgets.compiled_widgets.ui_main import Ui_MainWindow


class GlobalControls(QObject):
    """
    Controller for global application actions.

    Manages the main menu bar actions including file operations (save, open)
    and application settings. Connects menu actions to their respective handlers.

    Attributes:
        window: Reference to the main application window.
        save_button: Menu action for saving the current file.
        save_as_button: Menu action for saving with a new filename.
        open_button: Menu action for opening a file.
        open_settings_button: Menu action for opening the settings dialog.
    """

    def __init__(self, main_window: Ui_MainWindow, application_controller: "ApplicationController") -> None:
        """
        Initialize the global controls.

        Args:
            main_window: The main application window containing menu actions.
        """
        super().__init__(main_window)
        self._window = main_window
        self.application_controller = application_controller

        self._save_action = self._window.actionSave
        self._save_as_action = self._window.actionSave_As
        self._open_action = self._window.actionOpen
        self._settings_action = self._window.actionSettings

        self._export_action = self._window.actionExport_to_UMLSL_Sim
        self._import_action = self._window.actionImport_from_UMLSL_Sim

        self._setup_shortcuts()
        self._connect_signals()

    def _connect_signals(self) -> None:
        """Connect menu action signals to their handler methods."""
        self._save_action.triggered.connect(self._on_save)
        self._save_as_action.triggered.connect(self._on_save_as)
        self._open_action.triggered.connect(self._on_open)
        self._settings_action.triggered.connect(self._on_open_settings)
        self._export_action.triggered.connect(self._on_export)
        self._import_action.triggered.connect(self._on_import)

    def _setup_shortcuts(self) -> None:
        """Assign standard keyboard shortcuts to file actions."""
        self._open_action.setShortcuts(QKeySequence.Open)
        self._save_action.setShortcuts(QKeySequence.Save)
        self._save_as_action.setShortcuts(QKeySequence.SaveAs)
        if platform.system() == "Darwin":  # macOS
            self._settings_action.setShortcut(QKeySequence.Preferences)
        else:  # Windows / Linux
            self._settings_action.setShortcut("Ctrl+,")
        self._export_action.setShortcut("Ctrl+E")
        self._import_action.setShortcut("Ctrl+I")

    def _on_save(self) -> None:
        """Check if the current snapshot can be saved."""
        if self.application_controller.command_controller.get_current_snapshot_path() is None:
            self._on_save_as()
        else:
            try:
                self.application_controller.command_controller.save_traffic_snapshot()
            except CommandValidationError as exc:
                WarningDialog("Cannot save file", str(exc), self._window).exec()
            else:
                self._window.snackbar.show_message("File saved successfully.")

    def _on_save_as(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save current snapshot",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            self.application_controller.command_controller.save_as_traffic_snapshot(file_path)
        except CommandValidationError as exc:
            WarningDialog("Cannot save file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File saved successfully.")

    def _on_open(self) -> None:
        if self.application_controller.command_controller.get_data_changed_since_last_save():
            confirm = ConfirmDeletionDialog(
                "You have unsaved changes.\nDiscard them and open another file?",
                self._window,
                title="Unsaved Changes",
                confirm_text="Discard changes",
                cancel_text="Keep editing",
            ).exec()
            if confirm != QDialog.Accepted:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Open new snapshot",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            self.application_controller.command_controller.load_traffic_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot open file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File opened successfully.")

    def _on_open_settings(self) -> None:
        """Open the application settings dialog."""
        dialog = SettingsDialog(application_controller=self.application_controller, parent=self._window)
        dialog.exec()

    def _on_export(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Export current snapshot in JSON format compatible with UMLSL-Sim",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            self.application_controller.command_controller.export_snapshot(file_path)
        except CommandValidationError as exc:
            WarningDialog("Cannot export file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File exported successfully.")

    def _on_import(self) -> None:
        if self.application_controller.command_controller.get_data_changed_since_last_save():
            confirm = ConfirmDeletionDialog(
                "You have unsaved changes.\nDiscard them and open another file?",
                self._window,
                title="Unsaved Changes",
                confirm_text="Discard changes",
                cancel_text="Keep editing",
            ).exec()
            if confirm != QDialog.Accepted:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Import JSON file from UMLSL-Sim",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            self.application_controller.command_controller.import_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot import file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File imported successfully.")
