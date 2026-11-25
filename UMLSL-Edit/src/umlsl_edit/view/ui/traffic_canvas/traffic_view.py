"""
Traffic view for the UMLSL Traffic Editor.

Provides a custom QGraphicsView with zoom controls, dynamic grid background,
and coordinate labels for navigating the traffic canvas.
"""

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Slot
from PySide6.QtGui import QPainter, QPen, QTransform, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QPinchGesture

from umlsl_edit.controllers import ApplicationController
from umlsl_edit.view.view_constants import COLORS, DIMENSION


class TrafficView(QGraphicsView):
    """
    Custom graphics view for displaying and interacting with the traffic scene.

    Provides enhanced viewing capabilities including:
        - Mouse wheel and touchpad zoom with configurable constraints
        - Dynamic grid that adjusts density based on zoom level
        - Coordinate labels displayed at viewport edges
        - Smooth panning via scroll-hand drag mode

    The view uses an inverted Y-axis (positive Y points upward) to match
    standard mathematical coordinate conventions.

    Attributes:
        Inherits all attributes from QGraphicsView.
    """

    def __init__(self, scene: QGraphicsScene, application_controller: "ApplicationController", parent=None) -> None:
        """
        Initialize the traffic view with the given scene.

        Args:
            scene: The QGraphicsScene to display in this view.
            parent: The parent widget. Defaults to None.
        """
        super().__init__(scene, parent)
        self.application_controller = application_controller

        self._should_render_coordinate_system = (
            self.application_controller.view_event_handler.should_render_coordinate_system
        )
        self._should_render_grid = self.application_controller.view_event_handler.should_render_grid

        self.application_controller.view_event_handler.get_on_toggle_coordinate_system_signal().connect(
            self._on_toggle_coordinate_system
        )
        self.application_controller.view_event_handler.get_on_toggle_grid_signal().connect(
            self._on_toggle_grid
        )
        self.application_controller.view_event_handler.get_on_snapshot_reloaded_signal().connect(
            self.fit_world
        )

        self._fit_world_pending = False
        self._configure_view()
        self.scale(DIMENSION.INITIAL_ZOOM, -DIMENSION.INITIAL_ZOOM)

    @Slot(bool)
    def _on_toggle_coordinate_system(self, enabled: bool) -> None:
        self._should_render_coordinate_system = enabled
        self.viewport().update()

    @Slot(bool)
    def _on_toggle_grid(self, enabled: bool) -> None:
        self._should_render_grid = enabled
        self.viewport().update()

    def _configure_view(self) -> None:
        """Configure view settings for optimal rendering and interaction."""
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setBackgroundBrush(COLORS.GREEN)

        self.viewport().setAttribute(Qt.WA_AcceptTouchEvents)
        self.grabGesture(Qt.PinchGesture)

    # -------------------------------------------------------------------------
    # Gesture Handling (Pinch to Zoom)
    # -------------------------------------------------------------------------

    def event(self, event: QEvent) -> bool:
        """
        Intercept standard events to handle gestures.
        """
        if event.type() == QEvent.Gesture:
            return self._handle_gesture(event)
        return super().event(event)

    def _handle_gesture(self, event: QEvent) -> bool:
        """
        Route specific gesture types to their handlers.
        """
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            self._handle_pinch(pinch)
            return True
        return False

    def _handle_pinch(self, gesture: QPinchGesture) -> None:
        """
        Handle the pinch gesture for zooming.

        Uses manual anchoring (mapToScene) similar to wheelEvent to support
        the flipped Y-axis coordinate system.
        """
        change_flags = gesture.changeFlags()

        # Only zoom if the scale factor has changed
        if change_flags & QPinchGesture.ScaleFactorChanged:
            # QPinchGesture.scaleFactor() is a multiplier (e.g., 1.01 or 0.99)
            # representing the change since the last event.
            raw_factor = gesture.scaleFactor()

            # Apply your existing clamp logic
            scale_factor = self._calculate_clamped_scale(raw_factor)

            # Disable automatic anchoring to prevent jumping artifacts
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            # Get pinch center in scene coordinates
            anchor_pos = gesture.centerPoint().toPoint()
            old_scene_pos = self.mapToScene(anchor_pos)

            # Apply scale
            self.scale(scale_factor, scale_factor)

            # Translate to keep the pinch center stable
            new_scene_pos = self.mapToScene(anchor_pos)
            delta_scene = new_scene_pos - old_scene_pos
            self.translate(delta_scene.x(), delta_scene.y())

    # -------------------------------------------------------------------------
    # Zoom Handling
    # -------------------------------------------------------------------------

    @Slot()
    def fit_world(self) -> None:
        """Zoom and centre the view so that the whole world (where the lanes end) fits the viewport."""
        if not self.isVisible():
            # the viewport has no size of its own yet; fit once the view is laid out (see resizeEvent)
            self._fit_world_pending = True
            return
        self._fit_world_pending = False
        half_width, half_height = self.application_controller.data_controller.get_world_extent()
        viewport = self.viewport().size()
        if viewport.width() <= 0 or viewport.height() <= 0 or half_width <= 0 or half_height <= 0:
            return
        scale = DIMENSION.FIT_WORLD_MARGIN * min(
            viewport.width() / (2 * half_width), viewport.height() / (2 * half_height)
        )
        scale = min(max(scale, DIMENSION.MIN_ZOOM), DIMENSION.MAX_ZOOM)
        # positive y points up
        self.setTransform(QTransform.fromScale(scale, -scale))
        self.centerOn(0.0, 0.0)

    def button_zoom(self, amount: float) -> None:
        """
        Apply zoom from a button click, centered on the viewport.

        Args:
            amount: The zoom multiplier (>1 zooms in, <1 zooms out).
        """
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        scale_factor = self._calculate_clamped_scale(amount)
        self.scale(scale_factor, scale_factor)

        self._enforce_zoom_constraints()

    def resizeEvent(self, event) -> None:
        """
        Handle window resize events to maintain zoom constraints.

        Args:
            event: The resize event.
        """
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        super().resizeEvent(event)
        self._enforce_zoom_constraints()
        if self._fit_world_pending and self.isVisible():
            self.fit_world()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Handle zoom via mouse wheel or touchpad gestures.

        Implements anchor-under-mouse behavior manually to work correctly
        with the flipped Y-axis coordinate system.

        Args:
            event: The wheel event from mouse or touchpad.
        """
        delta = event.pixelDelta().y() or event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return

        is_touchpad = event.pixelDelta().y() != 0
        sensitivity = (
            DIMENSION.TOUCHPAD_ZOOM_SENSITIVITY
            if is_touchpad
            else DIMENSION.WHEEL_ZOOM_SENSITIVITY
        )
        scale_factor = self._calculate_clamped_scale(1 + delta * sensitivity)

        # Disable automatic anchoring (breaks with flipped Y-axis)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.setResizeAnchor(QGraphicsView.NoAnchor)

        # Get mouse position in scene coordinates before scaling
        old_pos = self.mapToScene(event.position().toPoint())

        self.scale(scale_factor, scale_factor)

        # Get new mouse position and translate to maintain anchor point
        new_pos = self.mapToScene(event.position().toPoint())
        delta_scene = new_pos - old_pos
        self.translate(delta_scene.x(), delta_scene.y())

        event.accept()

    def mousePressEvent(self, event) -> None:
        """
        Handle mouse press events.
        """
        self._mouse_press_pos = event.position()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """
        Handle mouse release events.

        Deselects the current entity if the click occurs on the empty background without dragging.
        """
        if hasattr(self, "_mouse_press_pos"):
            if (event.position() - self._mouse_press_pos).manhattanLength() < 5:
                if self.itemAt(event.position().toPoint()) is None:
                    self.application_controller.view_event_handler.entity_selected_view("")
        super().mouseReleaseEvent(event)

    def _calculate_clamped_scale(self, scale_factor: float) -> float:
        """
        Clamp the scale factor to keep zoom within valid bounds.

        Args:
            scale_factor: The desired scale multiplier.

        Returns:
            The clamped scale factor that keeps zoom within limits.
        """
        current_scale = abs(self.transform().m11())
        future_scale = current_scale * scale_factor

        if future_scale > DIMENSION.MAX_ZOOM:
            return DIMENSION.MAX_ZOOM / current_scale
        if future_scale < DIMENSION.MIN_ZOOM:
            return DIMENSION.MIN_ZOOM / current_scale
        return scale_factor

    def _enforce_zoom_constraints(self) -> None:
        """Ensure zoom level stays within valid range."""
        current_scale = abs(self.transform().m11())
        clamped = min(max(current_scale, DIMENSION.MIN_ZOOM), DIMENSION.MAX_ZOOM)
        if clamped != current_scale:
            self.scale(clamped / current_scale, clamped / current_scale)

    # -------------------------------------------------------------------------
    # Grid Drawing
    # -------------------------------------------------------------------------

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """
        Draw the background including the coordinate grid.

        Args:
            painter: The QPainter to use for drawing.
            rect: The exposed rectangle requiring a repaint.
        """
        super().drawBackground(painter, rect)

        if self._should_render_grid:
            grid_pen = QPen(COLORS.LAYER, DIMENSION.LANE_WIDTH)
            self._draw_grid(painter, grid_pen)

    def _draw_grid(self, painter: QPainter, pen: QPen) -> None:
        """
        Draw grid lines across the visible viewport area.

        Args:
            painter: The QPainter to use for drawing.
            pen: The pen style for grid lines.
        """
        viewport_rect = self.viewport().rect()
        step = self._get_grid_step()
        left, right, min_y, max_y = self._get_visible_bounds()

        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)

        # Draw vertical grid lines
        for x in self._iter_grid_values(left, right, step):
            screen_x = int(self.mapFromScene(QPointF(x, 0)).x())
            painter.drawLine(screen_x, 0, screen_x, viewport_rect.height())

        # Draw horizontal grid lines
        for y in self._iter_grid_values(min_y, max_y, step):
            screen_y = int(self.mapFromScene(QPointF(0, y)).y())
            painter.drawLine(0, screen_y, viewport_rect.width(), screen_y)

        painter.restore()

    def _get_grid_step(self) -> float:
        """
        Determine grid spacing based on current zoom level.

        The finest power of ten whose lines lie more than GRID_FINE_THRESHOLD pixels apart: one lane when zoomed in,
        ten lanes at the usual zoom, and a further tenfold for every tenfold the view is zoomed out from there, so
        the grid and its labels stay readable however far out the view is.

        Returns:
            The grid step size, in lanes.
        """
        scale = abs(self.transform().m11())
        step = DIMENSION.GRID_STEP_FINE
        while step * scale <= DIMENSION.GRID_FINE_THRESHOLD:
            step *= DIMENSION.GRID_STEP_COARSE / DIMENSION.GRID_STEP_FINE
        return step

    # -------------------------------------------------------------------------
    # Coordinate Labels
    # -------------------------------------------------------------------------

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """
        Draw foreground elements including coordinate labels.

        Args:
            painter: The QPainter to use for drawing.
            rect: The exposed rectangle requiring a repaint.
        """
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing)

        if self._should_render_coordinate_system:
            painter.setPen(QPen(COLORS.TEXT))
            self._draw_coordinate_labels(painter)

        painter.restore()

    def _draw_coordinate_labels(self, painter: QPainter) -> None:
        """
        Draw X and Y coordinate labels at the viewport edges.

        X-axis labels are drawn along the bottom edge.
        Y-axis labels are drawn along the right edge.

        Args:
            painter: The QPainter to use for drawing.
        """
        viewport_rect = self.viewport().rect()
        left, right, min_y, max_y = self._get_visible_bounds()
        step = self._get_label_step(painter, max(abs(left), abs(right), abs(min_y), abs(max_y)))

        # X-axis labels (bottom edge)
        for x in self._iter_grid_values(left, right, step):
            screen_x = int(self.mapFromScene(QPointF(x, 0)).x())
            painter.drawText(
                screen_x + DIMENSION.LABEL_PADDING,
                viewport_rect.height() - DIMENSION.LABEL_PADDING,
                str(int(x)),
            )

        # Y-axis labels (right edge)
        for y in self._iter_grid_values(min_y, max_y, step):
            screen_y = int(self.mapFromScene(QPointF(0, y)).y())
            label = str(int(y))
            text_width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(
                viewport_rect.width() - text_width - DIMENSION.LABEL_PADDING,
                screen_y - DIMENSION.LABEL_PADDING,
                label,
            )

    def _get_label_step(self, painter: QPainter, largest_value: float) -> float:
        """
        Spacing of the coordinate labels: the grid step, or a multiple of it (2, 5, 10, ...) wide enough that the
        widest label fits between two of them. Zoomed far out, the numbers outgrow the grid lines.
        """
        scale = abs(self.transform().m11())
        widest = painter.fontMetrics().horizontalAdvance(str(-int(math.ceil(largest_value))))
        needed = widest + 2 * DIMENSION.LABEL_PADDING
        grid_step = self._get_grid_step()
        for multiple in (1, 2, 5):
            factor = 1.0
            while grid_step * multiple * factor * scale < needed:
                factor *= 10
            candidate = grid_step * multiple * factor
            if multiple == 1 or candidate < best:
                best = candidate
        return best

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def _get_visible_bounds(self) -> tuple[float, float, float, float]:
        """
        Get the visible scene area boundaries.

        Returns:
            A tuple of (left, right, min_y, max_y) scene coordinates.
        """
        visible_scene = self.mapToScene(self.viewport().rect()).boundingRect()
        left = visible_scene.left()
        right = visible_scene.right()
        top = visible_scene.top()
        bottom = visible_scene.bottom()
        return left, right, min(top, bottom), max(top, bottom)

    @staticmethod
    def _iter_grid_values(start: float, end: float, step: float):
        """
        Generate grid coordinate values within the specified range.

        Args:
            start: The starting coordinate value.
            end: The ending coordinate value.
            step: The spacing between grid lines.

        Yields:
            Coordinate values aligned to the grid step.
        """
        val = math.floor(start / step) * step
        while val <= end:
            yield val
            val += step
