from PySide6.QtCore import QSize
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget

from umlsl_edit.view.ui.lists.edit_dialogs.confirm_deletion_dialog import (
    ConfirmDeletionDialog,
)


class SaveChangesDialog(ConfirmDeletionDialog):
    """
    Ask whether to save unsaved changes before they are replaced.

    The confirmation dialog with a third button in front. ``exec()`` returns
    ``SAVE``, ``DISCARD`` or ``CANCEL``.
    """

    SAVE = 2
    DISCARD = ConfirmDeletionDialog.DialogCode.Accepted.value
    CANCEL = ConfirmDeletionDialog.DialogCode.Rejected.value

    def __init__(
            self,
            message: str,
            parent: QWidget | None = None,
            title: str | None = None,
    ) -> None:
        super().__init__(
            message,
            parent,
            title=title,
            confirm_text="Don't save",
            cancel_text="Cancel",
        )
        self.b_save = QPushButton("Save", self)
        self.b_save.setObjectName("b_save")
        self.b_save.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.b_save.setMinimumSize(QSize(32, 32))
        self.b_save.setMaximumSize(QSize(16777215, 32))
        # The only save icons are light, so this light button has none. The
        # style is set on the button itself: an ``#b_save`` rule added to the
        # dialog's style sheet does not reach it.
        self.b_save.setStyleSheet(
            "QPushButton { background-color: #F9F9F9; color: #011C26; border-radius: 16px; }"
            "QPushButton:hover { background-color: #DDE3E6; }"
            "QPushButton:pressed { background-color: #F9F9F9; }"
        )
        self.b_save.setDefault(True)
        self.b_save.clicked.connect(lambda: self.done(self.SAVE))
        self.horizontalLayout.insertWidget(0, self.b_save)
        # The message names the snapshot, so it can be longer than one line.
        self.l_content.setWordWrap(True)
