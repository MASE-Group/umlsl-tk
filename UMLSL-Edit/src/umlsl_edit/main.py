"""
Main entry point for the UMLSL-Edit application.
"""
import os
import sys
import warnings

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from umlsl_edit.commands.command import CommandValidationError
from umlsl_edit.controllers import ApplicationController
from umlsl_edit.model.errors.errors import BaseError
from umlsl_edit.services.editor_instance import (
    EditorInstanceServer,
    forward_to_running_editor,
    import_request,
)
from umlsl_edit.view.ui.exception_handling.exception_handler import (
    ExceptionHandler,
)
from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog
from umlsl_edit.view.ui.main_window import MainWindow


class Main:
    """Main Application Controller."""

    def __init__(self):
        self.application_controller = ApplicationController()

        self.open_window()

    def open_window(self) -> None:
        """
        Launch the main window.

        ``python -m umlsl_edit.main FILE`` opens FILE. With
        ``--import-from-sim FILE`` (how UMLSL-Sim opens the editor), an editor
        that is already open imports FILE instead and this process ends.
        Otherwise this window opens and imports FILE.
        """
        app = QApplication(sys.argv)

        sim_file = import_request(sys.argv)
        if sim_file is not None and forward_to_running_editor(os.path.abspath(sim_file)):
            sys.exit(0)

        app.setApplicationName("UMLSL-Edit")
        app.setApplicationDisplayName("UMLSL-Edit")

        # The icon ships inside the package, so resolve it relative to this module.
        icon_path = os.path.join(
            os.path.dirname(__file__), "view", "widgets", "qt_widgets", "icons", "icon.png"
        )
        app.setWindowIcon(QIcon(icon_path))

        window = MainWindow(self.application_controller)

        exception_handler = ExceptionHandler(parent=window)
        # sys.excepthook = exception_handler.handle_exception
        warnings.showwarning = exception_handler.handle_warning

        # The first open editor receives the snapshots that UMLSL-Sim sends.
        instance_server = EditorInstanceServer(window)
        instance_server.import_requested.connect(window.global_controls.receive_from_simulator)
        instance_server.listen()

        window.show()

        if sim_file is not None:
            QTimer.singleShot(0, lambda: window.global_controls.open_from_simulator(sim_file))
        elif len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.exists(file_path):
                QTimer.singleShot(0, lambda: self.load_command_line_file(file_path, window))

        sys.exit(app.exec())

    def load_command_line_file(self, file_path: str, window) -> None:
        try:
            notes = self.application_controller.command_controller.load_traffic_snapshot(file_path)
        except (BaseError, CommandValidationError) as exc:
            WarningDialog("Cannot open file", str(exc), window).exec()
        else:
            window.snackbar.show_message("File opened successfully.")
            window.global_controls.show_import_notes(notes)


if __name__ == "__main__":
    Main()
