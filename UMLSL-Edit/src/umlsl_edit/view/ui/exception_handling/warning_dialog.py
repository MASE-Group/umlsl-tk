from PySide6.QtWidgets import QDialog, QWidget

from umlsl_edit.view.widgets.compiled_widgets.ui_error_dialog import (
    Ui_Error_Dialog,
)


class WarningDialog(QDialog, Ui_Error_Dialog):
    """
    Dialog for displaying warning messages to the user.

    This dialog provides a simple interface for showing warning messages. It inherits
    from both QDialog for dialog behavior and Ui_Error_Dialog for the auto-generated
    UI layout.

    Attributes:
        Inherits all attributes from QDialog and Ui_Error_Dialog.
    """

    def __init__(self, title: str, message: str, parent: QWidget | None = None) -> None:
        """
        Initialize the warning dialog.

        Args:
            title: The dialog title to display.
            message: The warning message to display in the dialog.
            parent: The parent widget for this dialog. Defaults to None.
        """
        super().__init__(parent)
        self.setupUi(self)
        self._title_label = self.l_titel
        self._message_label = self.l_content
        self._title_label.setText(title)
        self._message_label.setText(message)
