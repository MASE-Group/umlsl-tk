"""
Base entity list model for the UMLSL Traffic Editor.

Provides an abstract base class for QML list models that display selectable
entity collections. Handles common functionality including selection state
management and row operations.
"""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QTimer, Signal, Slot

from umlsl_edit.controllers.view_event_contract import ViewEventHandler
from umlsl_edit.model.entities.entity import Entity


class EntityModel(QAbstractListModel):
    """
    Abstract base class for entity list models.

    Provides common functionality for list models that display selectable
    entities in QML views. Subclasses should define additional roles for
    entity-specific properties.

    Features:
        - Selection state tracking and synchronization
        - Entity add/remove/update operations
        - Base role for selection state exposed to QML

    Attributes:
        IsSelectedRole: Role ID for the selection state.
        NextRole: Starting role ID for subclass-defined roles.
    """

    IsSelectedRole = Qt.UserRole + 1
    NextRole = IsSelectedRole + 1

    edit_requested = Signal(int)  # Emits row index when edit is requested

    def __init__(self, parent=None) -> None:
        """
        Initialize the entity model.

        Args:
            parent: The parent QObject. Defaults to None.
        """
        super().__init__(parent)
        self._data: list[Entity] = []
        self._selected_uid: str = ""
        self._view_event_handler: ViewEventHandler | None = None
        # Track deferred removals so rapid remove/add cycles don't drop entities.
        self._pending_removals: set[str] = set()

    def connect_signal(self, view_event_handler: ViewEventHandler) -> None:
        """
        Connect to the view event handler for selection synchronization.

        Args:
            view_event_handler: The handler providing selection change signals.
        """
        self._view_event_handler = view_event_handler
        selection_signal = self._view_event_handler.get_on_selection_changed_signal()
        selection_signal.connect(self._handle_selection_changed)

    # -------------------------------------------------------------------------
    # Entity Operations
    # -------------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> None:
        """
        Add an entity to the model.

        Args:
            entity: The entity to add.
        """
        # Cancel any pending removal for the same UID.
        self._pending_removals.discard(entity.uid)

        existing_row = self._get_row_by_uid(entity.uid)
        if existing_row is not None:
            self._data[existing_row] = entity
            index = self.index(existing_row)
            self.dataChanged.emit(index, index, list(self.roleNames().keys()))
            return

        row = len(self._data)
        self.beginInsertRows(QModelIndex(), row, row)
        self._data.append(entity)
        self.endInsertRows()

    def remove_entity(self, entity: Entity) -> None:
        """
        Remove an entity from the model.

        Defers removal to the next event loop iteration to prevent
        conflicts with QML signal handlers that may be in progress.

        Args:
            entity: The entity to remove.
        """
        if self._get_row_by_uid(entity.uid) is None:
            return

        self._pending_removals.add(entity.uid)

        # Defer removal to next event loop iteration to avoid destroying
        # objects while QML signal handlers are still in progress.
        QTimer.singleShot(0, lambda uid=entity.uid: self._do_remove_entity(uid))

    def _do_remove_entity(self, uid: str) -> None:
        """
        Perform the actual entity removal.

        Args:
            uid: The UID of the entity to remove.
        """
        if uid not in self._pending_removals:
            return

        row = self._get_row_by_uid(uid)
        if row is None:
            self._pending_removals.discard(uid)
            return

        entity_to_remove = self._data[row]
        self.beginRemoveRows(QModelIndex(), row, row)
        self._data.remove(entity_to_remove)
        self.endRemoveRows()
        self._pending_removals.discard(uid)

    def clear_all(self) -> None:
        """
        Remove all entities from the model in a single reset.
        """
        if not self._data:
            return

        self.beginResetModel()
        self._data.clear()
        self._selected_uid = ""
        self._pending_removals.clear()
        self.endResetModel()

    def _get_row_by_uid(self, uid: str) -> int | None:
        """
        Get the row index for an entity by UID.

        Args:
            uid: The UID of the entity.

        Returns:
            The row index if found, otherwise None.
        """
        for i, existing in enumerate(self._data):
            if existing.uid == uid:
                return i
        return None

    def update_entity(self, entity: Entity) -> None:
        """
        Notify that an entity's data has changed.

        Args:
            entity: The entity that was updated.
        """
        row = self._get_row_by_uid(entity.uid)
        if row is None:
            return

        # Update by UID even if the instance changed after a remove/add cycle.
        index = self.index(row)
        self.dataChanged.emit(index, index, list(self.roleNames().keys()))

    def get_entity_at(self, row: int) -> Entity:
        """
        Get the entity at the specified row index.

        Args:
            row: The row index.

        Returns:
            The entity at the given row.

        Raises:
            IndexError: If the row is out of bounds.
        """
        return self._data[row]

    # -------------------------------------------------------------------------
    # QAbstractListModel Implementation
    # -------------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """
        Return the number of rows in the model.

        Args:
            parent: The parent index (unused for flat lists).

        Returns:
            The number of entities in the model.
        """
        return len(self._data)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> object | None:
        """
        Return data for the specified index and role.

        Handles the IsSelectedRole for selection state. Subclasses should
        call super().data() first and handle additional roles if None is returned.

        Args:
            index: The model index.
            role: The data role to retrieve.

        Returns:
            The data for the role, or None if not applicable.
        """
        if not index.isValid():
            return None

        if role == EntityModel.IsSelectedRole:
            entity = self._data[index.row()]
            return entity.uid == self._selected_uid

        return None

    def roleNames(self) -> dict[int, bytes]:
        """
        Return the role names mapping for QML access.

        Subclasses should call super().roleNames() and update with additional roles.

        Returns:
            Dictionary mapping role IDs to QML property names.
        """
        return {
            EntityModel.IsSelectedRole: b"role_is_selected",
        }

    # -------------------------------------------------------------------------
    # Selection Handling
    # -------------------------------------------------------------------------

    @Slot(str)
    def _handle_selection_changed(self, uid: str) -> None:
        """
        Handle global selection change events.

        Updates the selected UID and emits dataChanged for all rows to
        refresh selection state display.

        Args:
            uid: The UID of the newly selected entity.
        """
        if self._selected_uid == uid:
            return

        self._selected_uid = uid

        if self._data:
            first_index = self.index(0)
            last_index = self.index(len(self._data) - 1)
            self.dataChanged.emit(first_index, last_index, [EntityModel.IsSelectedRole])

    @Slot(int)
    def select_row(self, row: int) -> None:
        """
        Handle row selection from QML.

        Called when a list row is clicked in the UI. Notifies the view
        event handler of the selection.

        Args:
            row: The index of the selected row.
        """
        if not (0 <= row < len(self._data)):
            return

        entity = self._data[row]
        if self._view_event_handler:
            self._view_event_handler.entity_selected_view(entity.uid)

    @Slot(int)
    def handle_button_click(self, row: int) -> None:
        """
        Handle button click for a specific row.

        Emits the edit_requested signal with the row index. Connect to this
        signal to open an edit dialog with the appropriate parent widget.

        Args:
            row: The index of the row whose button was clicked.
        """
        if 0 <= row < len(self._data):
            self.edit_requested.emit(row)
