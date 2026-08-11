"""
Selectable graphics item for the UMLSL Traffic Editor.

Provides a base class for graphics items that support selection, dragging,
and view panning behavior. Items can be clicked to toggle selection and
dragged when selected.
"""

from PySide6.QtCore import QPointF, Qt, Slot
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneHoverEvent,
    QGraphicsSceneMouseEvent,
    QGraphicsView,
)

from umlsl_edit.controllers import ApplicationController


class SelectableGraphicsItem(QGraphicsItem):
    """
    Base class for selectable and draggable graphics items.

    Provides unified behavior for:
        - Click-to-select/deselect functionality
        - Drag movement when selected (with optional axis constraints)
        - View panning when dragging an unselected item
        - Hover state tracking with cursor feedback

    Subclasses should implement the hook methods to respond to state changes:
        - on_selection_changed(is_selected)
        - on_hover_changed(is_hovered)
        - on_move_committed(delta_x, delta_y)

    Attributes:
        is_selected: Whether this item is currently selected.
        is_hovered: Whether the mouse is currently over this item.
        application_controller: Reference to the application controller.
    """

    AXIS_FREE = 0
    AXIS_X_ONLY = 1
    AXIS_Y_ONLY = 2

    def __init__(self, application_controller: ApplicationController) -> None:
        """
        Initialize the selectable graphics item.

        Args:
            application_controller: The application controller for handling
                selection events and commands.
        """
        super().__init__()

        self.is_hovered = False
        self.application_controller = application_controller
        self.is_selected = False

        self._movement_constraint = self.AXIS_FREE
        self._drag_start_pos: QPointF | None = None
        self._pan_start_screen_pos: QPointF | None = None
        self._is_panning = False

        self._configure_item_flags()
        self._connect_selection_signal()

    def _configure_item_flags(self) -> None:
        """Configure Qt item flags for movement and event handling."""
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)

    def _connect_selection_signal(self) -> None:
        """Connect to the global selection changed signal."""
        selection_signal = (
            self.application_controller.view_event_handler.get_on_selection_changed_signal()
        )
        selection_signal.connect(self._on_global_selection_change)

    def check_current_selection(self) -> None:
        self._on_global_selection_change(
            self.application_controller.view_event_handler.get_current_selected_uid())

    # -------------------------------------------------------------------------
    # Movement Constraints
    # -------------------------------------------------------------------------

    def set_movement_constraint(self, constraint: int) -> None:
        """
        Set the axis constraint for item movement.

        Args:
            constraint: One of AXIS_FREE, AXIS_X_ONLY, or AXIS_Y_ONLY.
        """
        self._movement_constraint = constraint

    def itemChange(self, change: int, value):
        """
        Apply movement constraints when the item position changes.

        Args:
            change: The type of change occurring.
            value: The new value for the change.

        Returns:
            The potentially modified value.
        """
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            current_pos = self.pos()

            if self._movement_constraint == self.AXIS_X_ONLY:
                new_pos.setY(current_pos.y())
            elif self._movement_constraint == self.AXIS_Y_ONLY:
                new_pos.setX(current_pos.x())

            return new_pos

        return super().itemChange(change, value)

    # -------------------------------------------------------------------------
    # Hover Events
    # -------------------------------------------------------------------------

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Handle mouse entering the item area.

        Updates hover state, cursor, and notifies subclasses.

        Args:
            event: The hover event.
        """
        self.is_hovered = True
        self._update_cursor_for_state()
        self.on_hover_changed(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        """
        Handle mouse leaving the item area.

        Resets hover state, cursor, and notifies subclasses.

        Args:
            event: The hover event.
        """
        self.is_hovered = False
        self.setCursor(Qt.ArrowCursor)
        self.on_hover_changed(False)
        super().hoverLeaveEvent(event)

    def _update_cursor_for_state(self) -> None:
        """Update the cursor based on the current selection state."""
        if self.is_selected:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.PointingHandCursor)

    # -------------------------------------------------------------------------
    # Mouse Events
    # -------------------------------------------------------------------------

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse press to initiate drag or pan.

        Args:
            event: The mouse press event.
        """
        self._drag_start_pos = event.scenePos()
        self._pan_start_screen_pos = event.screenPos()
        self._is_panning = False

        self.setCursor(Qt.ClosedHandCursor)
        self.setFlag(QGraphicsItem.ItemIsMovable, self.is_selected)

        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse release to complete drag, pan, or click.

        Args:
            event: The mouse release event.
        """
        if self._is_panning:
            self._finish_panning()
        else:
            self._handle_drag_or_click(event)

        self._update_cursor_for_state()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Handle mouse movement for dragging or panning.

        If selected, moves the item. If not selected, pans the view.

        Args:
            event: The mouse move event.
        """
        if self.is_selected:
            super().mouseMoveEvent(event)
        else:
            self._handle_view_panning(event)

    # -------------------------------------------------------------------------
    # Panning Logic
    # -------------------------------------------------------------------------

    def _handle_view_panning(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Pan the view when dragging an unselected item.

        Args:
            event: The mouse move event.
        """
        current_screen_pos = event.screenPos()
        delta = current_screen_pos - self._pan_start_screen_pos

        if delta.manhattanLength() > 0 or self._is_panning:
            self._is_panning = True
            self._pan_start_screen_pos = current_screen_pos
            self._apply_scroll_delta(event.widget(), delta)

    def _apply_scroll_delta(self, viewport, delta) -> None:
        """
        Apply scroll delta to the parent view's scrollbars.

        Args:
            viewport: The viewport widget from the event.
            delta: The screen-space delta to scroll.
        """
        if not viewport or not viewport.parent():
            return

        view = viewport.parent()
        if not isinstance(view, QGraphicsView):
            return

        h_scroll = view.horizontalScrollBar()
        v_scroll = view.verticalScrollBar()
        h_scroll.setValue(h_scroll.value() - delta.x())
        v_scroll.setValue(v_scroll.value() - delta.y())

    def _finish_panning(self) -> None:
        """Reset position after panning if the item was moved."""
        if self._has_moved():
            self.setPos(0, 0)

    # -------------------------------------------------------------------------
    # Drag and Click Logic
    # -------------------------------------------------------------------------

    def _handle_drag_or_click(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Distinguish between a drag and a click, then handle appropriately.

        Args:
            event: The mouse release event.
        """
        drag_distance = (event.scenePos() - self._drag_start_pos).manhattanLength()
        was_dragged = drag_distance > 0

        if was_dragged and self.is_selected and self._has_moved():
            self._commit_move()
        elif not was_dragged:
            self._toggle_selection()

    def _has_moved(self) -> bool:
        """
        Check if the item has moved from its original position.

        Returns:
            True if the item's position is not at the origin.
        """
        return self.pos().manhattanLength() > 0

    def _commit_move(self) -> None:
        """Commit the item movement and reset local position."""
        self.on_move_committed(self.x(), self.y())
        self.setPos(0, 0)

    # -------------------------------------------------------------------------
    # Selection Logic
    # -------------------------------------------------------------------------

    def _toggle_selection(self) -> None:
        """Toggle selection state by notifying the view event handler."""
        entity = self.data(0)
        if entity:
            self.application_controller.view_event_handler.entity_selected_view(
                entity.uid
            )

    @Slot(str)
    def _on_global_selection_change(self, selected_uid: str) -> None:
        """
        Handle global selection change events.

        Updates this item's selection state based on whether its entity
        matches the newly selected UID.

        Args:
            selected_uid: The UID of the newly selected entity.
        """
        entity = self.data(0)
        if not entity:
            return

        should_be_selected = entity.uid == selected_uid

        if self.is_selected != should_be_selected:
            self.is_selected = should_be_selected
            self.on_selection_changed(self.is_selected)
            self._update_cursor_for_state()
            self.update()

    # -------------------------------------------------------------------------
    # Subclass Hooks
    # -------------------------------------------------------------------------

    def on_move_committed(self, delta_x: float, delta_y: float) -> None:
        """
        Called when an item drag is completed.

        Override in subclasses to handle position updates.

        Args:
            delta_x: The horizontal distance moved.
            delta_y: The vertical distance moved.
        """
        pass

    def on_selection_changed(self, is_selected: bool) -> None:
        """
        Called when selection state changes.

        Override in subclasses to update visual appearance.

        Args:
            is_selected: The new selection state.
        """
        pass

    def on_hover_changed(self, is_hovered: bool) -> None:
        """
        Called when hover state changes.

        Override in subclasses to update visual appearance.

        Args:
            is_hovered: The new hover state.
        """
        pass
