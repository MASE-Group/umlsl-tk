"""
Global exception and warning handlers for the UMLSL Traffic Editor.

Provides user-friendly error dialogs for uncaught exceptions and warnings.
"""

import sys
import traceback
from typing import Optional

from PySide6.QtWidgets import QMessageBox, QWidget

from umlsl_edit.view.ui.exception_handling.warning_dialog import WarningDialog


class ExceptionHandler:
    """
    Handler for displaying user-friendly error and warning dialogs.

    This class provides methods that can be installed as sys.excepthook
    and warnings.showwarning to redirect errors and warnings to dialogs
    centered on the parent widget.

    Attributes:
        _parent: The parent widget for dialog centering (typically the main window).
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the exception handler.

        Args:
            parent: The parent widget for dialogs (typically the main window).
        """
        self._parent = parent

    def set_parent(self, parent: QWidget) -> None:
        """
        Set the parent widget for dialogs.

        Args:
            parent: The parent widget (typically the main window).
        """
        self._parent = parent

    def handle_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """
        Handle uncaught exceptions by displaying a critical error dialog.

        This method can be installed as sys.excepthook to catch all
        unhandled exceptions in the application.

        Args:
            exc_type: The exception type.
            exc_value: The exception instance.
            exc_traceback: The traceback object.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        box = QMessageBox(self._parent)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("Critical Error")
        box.setText(f"An unexpected error occurred:\n{exc_value}")
        box.setDetailedText(error_msg)
        box.setStandardButtons(QMessageBox.Ok)
        box.exec()

    def handle_warning(self, message, category, filename, lineno, file=None, line=None) -> None:
        """
        Handle warnings by displaying a warning dialog.

        This method can be installed with warnings.showwarning to redirect
        warnings.warn() calls to a user-friendly dialog.

        Args:
            message: The warning message.
            category: The warning category class.
            filename: The source file where the warning was issued.
            lineno: The line number where the warning was issued.
            file: Unused (for compatibility with warnings.showwarning signature).
            line: Unused (for compatibility with warnings.showwarning signature).
        """
        msg_text = str(message)
        title = f"{category.__name__}"

        dialog = WarningDialog(title, msg_text, self._parent)
        dialog.exec()
