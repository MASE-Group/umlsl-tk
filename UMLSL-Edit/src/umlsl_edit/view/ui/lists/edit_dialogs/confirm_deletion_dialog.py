from PySide6.QtWidgets import QDialog, QWidget

from umlsl_edit.view.widgets.compiled_widgets.ui_delete_dialog import (
    Ui_Delete_Dialog,
)


class ConfirmDeletionDialog(QDialog, Ui_Delete_Dialog):
    """
    Modal dialog for confirming destructive actions.

    Displays a title, a message, and optional custom labels for confirm/cancel buttons.
    """

    def __init__(
            self,
            message: str,
            parent: QWidget | None = None,
            title: str | None = None,
            confirm_text: str | None = None,
            cancel_text: str | None = None,
    ) -> None:
        """
        Initialize the confirmation dialog.

        Args:
            message: Main confirmation message shown in the dialog.
            parent: Optional parent widget for modal ownership.
            title: Optional dialog title override.
            confirm_text: Optional label override for the confirm button.
            cancel_text: Optional label override for the cancel button.
        """
        super().__init__(parent)
        self.setupUi(self)
        if title:
            self.l_title.setText(title)
        if confirm_text:
            self.b_delete.setText(confirm_text)
        if cancel_text:
            self.b_cancel.setText(cancel_text)
        self.l_content.setText(message)
