"""
Global controls for the UMLSL Traffic Editor.

Handles global UI actions such as save, open, and settings from the main menu bar.
"""
import platform
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
)

from umlsl_edit.commands.command import CommandValidationError
from umlsl_edit.controllers import ApplicationController
from umlsl_edit.model.errors.errors import BaseError
from umlsl_edit.services.simulator_launcher import (
    SimulatorNotInstalledError,
    SimulatorProcess,
    launch_simulator,
    scenario_key,
    scenarios_dir,
)
from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog
from umlsl_edit.view.ui.lists.edit_dialogs.confirm_deletion_dialog import (
    ConfirmDeletionDialog,
)
from umlsl_edit.view.ui.lists.edit_dialogs.save_changes_dialog import (
    SaveChangesDialog,
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
        self._simulate_action = self._window.actionSimulate_in_UMLSL_Sim

        self._exported_from: dict[str, str] = {}
        """Scenario key -> snapshot file it was exported from this session. Exporting
        the same file under the same key again replaces it without asking."""
        self._last_key: str | None = None
        self._simulators: list[SimulatorProcess] = []

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
        self._simulate_action.triggered.connect(self._on_simulate)

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
        self._simulate_action.setShortcut("Ctrl+R")

    def _on_save(self) -> bool:
        """Save the snapshot, through 'Save As' if it has no file yet. Returns whether it was saved."""
        if self.application_controller.command_controller.get_current_snapshot_path() is None:
            return self._on_save_as()
        try:
            self.application_controller.command_controller.save_traffic_snapshot()
        except CommandValidationError as exc:
            WarningDialog("Cannot save file", str(exc), self._window).exec()
            return False
        self._window.snackbar.show_message("File saved successfully.")
        return True

    def _on_save_as(self) -> bool:
        """Ask for a file and save the snapshot there. Returns whether it was saved."""
        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save current snapshot",
            "",
            "JSON Files (*.json)"
        )
        if not file_path:
            return False
        try:
            self.application_controller.command_controller.save_as_traffic_snapshot(file_path)
        except CommandValidationError as exc:
            WarningDialog("Cannot save file", str(exc), self._window).exec()
            return False
        self._window.snackbar.show_message("File saved successfully.")
        return True

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
            notes = self.application_controller.command_controller.load_traffic_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot open file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File opened successfully.")
            self.show_import_notes(notes)

    def _on_open_settings(self) -> None:
        """Open the application settings dialog."""
        dialog = SettingsDialog(application_controller=self.application_controller, parent=self._window)
        dialog.exec()

    def _on_export(self) -> None:
        if not self._confirm_simulator_compatibility("export"):
            return
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
            notes = self.application_controller.command_controller.import_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot import file", str(exc), self._window).exec()
        else:
            self._window.snackbar.show_message("File imported successfully.")
            self.show_import_notes(notes)

    def show_import_notes(self, notes: list[str]) -> None:
        """Tell the user what an import from UMLSL-Sim changed to fit the editor."""
        if notes:
            WarningDialog(
                "Adjusted for UMLSL-Edit",
                "The snapshot was opened with these changes:\n\n" + "\n".join(f"• {n}" for n in notes),
                self._window,
            ).exec()

    # ------------------------------------------------------------------
    # Open a snapshot sent by UMLSL-Sim
    # ------------------------------------------------------------------

    def receive_from_simulator(self, file_path: str) -> None:
        """
        Open a snapshot sent by UMLSL-Sim once no dialog is waiting for the user.

        Snapshots arrive at any time. Opening one on top of a dialog would
        nest a second dialog, so it waits until the dialog has closed.
        """
        if QApplication.activeModalWidget() is not None:
            QTimer.singleShot(300, lambda: self.receive_from_simulator(file_path))
            return
        self.open_from_simulator(file_path)

    def open_from_simulator(self, file_path: str) -> None:
        """
        Replace the scenario with a snapshot that UMLSL-Sim saved and sent here.

        If the current scenario has unsaved changes, the user first chooses to
        save them, to drop them, or to keep editing and ignore the snapshot.
        """
        self._bring_window_to_front()
        controller = self.application_controller.command_controller
        if controller.get_data_changed_since_last_save():
            answer = SaveChangesDialog(
                f"UMLSL-Sim sent the snapshot '{Path(file_path).stem}'.\n"
                "Save your unsaved changes before it replaces the current scenario?",
                self._window,
                title="Unsaved Changes",
            ).exec()
            if answer == SaveChangesDialog.CANCEL:
                return
            if answer == SaveChangesDialog.SAVE and not self._on_save():
                return
        try:
            notes = controller.import_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot open the snapshot from UMLSL-Sim", str(exc), self._window).exec()
            return
        self._window.snackbar.show_message(f"Opened '{Path(file_path).stem}' from UMLSL-Sim.")
        self.show_import_notes(notes)

    def _bring_window_to_front(self) -> None:
        if self._window.isMinimized():
            self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    # ------------------------------------------------------------------
    # Simulate in UMLSL-Sim
    # ------------------------------------------------------------------

    def _on_simulate(self) -> None:
        """Check the snapshot, export it to UMLSL-Sim, and open the simulator on it."""
        if not self._confirm_simulator_compatibility("simulate"):
            return
        try:
            folder = scenarios_dir()
        except SimulatorNotInstalledError as exc:
            WarningDialog("UMLSL-Sim not found", str(exc), self._window).exec()
            return

        key = self._ask_scenario_key(folder)
        if key is None:
            return
        try:
            self.application_controller.command_controller.export_snapshot(str(folder / f"{key}.json"))
        except CommandValidationError as exc:
            WarningDialog("Cannot export to UMLSL-Sim", str(exc), self._window).exec()
            return
        current = self.application_controller.command_controller.get_current_snapshot_path()
        if current is not None:
            self._exported_from[key] = current
        self._last_key = key

        try:
            simulator = launch_simulator(key)
        except OSError as exc:
            WarningDialog("Cannot start UMLSL-Sim", str(exc), self._window).exec()
            return
        self._simulators.append(simulator)
        self._window.snackbar.show_message(f"Exported '{key}'. Opening UMLSL-Sim…")
        QTimer.singleShot(3000, lambda: self._report_simulator_failure(simulator))

    def _confirm_simulator_compatibility(self, verb: str) -> bool:
        """
        Tell the user why UMLSL-Sim cannot run the snapshot, or how it will differ.

        Args:
            verb: "simulate" or "export", used in the dialog texts.

        Returns:
            True if the action may go ahead: there are no errors, and the user
            accepted any warnings.
        """
        scenario = self.application_controller.command_controller.check_simulator_export()
        if scenario.errors:
            WarningDialog(
                f"Cannot {verb} this scenario",
                "UMLSL-Sim cannot run this scenario:\n\n" + _bullets(scenario.errors),
                self._window,
            ).exec()
            return False
        if scenario.warnings:
            answer = ConfirmDeletionDialog(
                "UMLSL-Sim can run this scenario, but:\n\n" + _bullets(scenario.warnings),
                self._window,
                title=f"{verb.capitalize()} anyway?",
                confirm_text=f"{verb.capitalize()} anyway",
                cancel_text="Keep editing",
            ).exec()
            return answer == QDialog.Accepted
        return True

    def _ask_scenario_key(self, folder: Path) -> str | None:
        """Ask for the scenario name; ``None`` if the user cancels."""
        current = self.application_controller.command_controller.get_current_snapshot_path()
        suggestion = (scenario_key(Path(current).stem) if current else "") or self._last_key or "edit_scenario"
        while True:
            text, accepted = QInputDialog.getText(
                self._window,
                "Simulate in UMLSL-Sim",
                "Scenario name in UMLSL-Sim\n(lower case letters, digits and _):",
                QLineEdit.Normal,
                suggestion,
            )
            if not accepted:
                return None
            key = scenario_key(text)
            if not key:
                WarningDialog(
                    "Invalid scenario name",
                    "Use at least one letter or digit.",
                    self._window,
                ).exec()
                continue
            exported_before = current is not None and self._exported_from.get(key) == current
            if exported_before or not (folder / f"{key}.json").exists():
                return key
            replace = ConfirmDeletionDialog(
                f"UMLSL-Sim already has a scenario named '{key}'.\nReplace it?",
                self._window,
                title="Replace scenario?",
                confirm_text="Replace",
                cancel_text="Choose another name",
            ).exec()
            if replace == QDialog.Accepted:
                return key
            suggestion = key

    def _report_simulator_failure(self, simulator: SimulatorProcess) -> None:
        """Show why UMLSL-Sim closed, if it stopped with an error right after starting."""
        failure = simulator.failure()
        if failure is not None:
            WarningDialog("UMLSL-Sim stopped", failure, self._window).exec()
        self._simulators = [s for s in self._simulators if s.process.poll() is None]


def _bullets(issues) -> str:
    return "\n".join(f"• {issue.message}" for issue in issues)
