"""
Traffic view for the UMLSL Traffic Editor.

Provides a custom QGraphicsView with zoom controls, dynamic grid background,
and coordinate labels for navigating the traffic canvas.
"""

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Slot
from PySide6.QtGui import QPainter, QPen, QWheelEvent
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
        min_scale = self._get_min_scale_for_scene()

        if future_scale > DIMENSION.MAX_ZOOM:
            return DIMENSION.MAX_ZOOM / current_scale
        if future_scale < min_scale:
            return min_scale / current_scale
        return scale_factor

    def _enforce_zoom_constraints(self) -> None:
        """Ensure zoom level stays within valid range for current viewport size."""
        current_scale = abs(self.transform().m11())
        min_scale = self._get_min_scale_for_scene()

        if current_scale < min_scale:
            self.scale(min_scale / current_scale, min_scale / current_scale)

    def _get_min_scale_for_scene(self) -> float:
        """
        Calculate the minimum zoom scale to fill the viewport with the scene.

        Returns:
            The minimum scale factor ensuring the scene fills the viewport.
        """
        viewport_size = self.viewport().size()
        scene_rect = self.scene().sceneRect()

        if scene_rect.width() == 0 or scene_rect.height() == 0:
            return DIMENSION.MIN_ZOOM

        scale_x = viewport_size.width() / scene_rect.width()
        scale_y = viewport_size.height() / scene_rect.height()
        return max(scale_x, scale_y, DIMENSION.MIN_ZOOM)

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

        Returns:
            The grid step size (coarse when zoomed out, fine when zoomed in).
        """
        scale = self.transform().m11()
        if scale <= DIMENSION.GRID_FINE_THRESHOLD:
            return DIMENSION.GRID_STEP_COARSE
        return DIMENSION.GRID_STEP_FINE

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
        step = self._get_grid_step()
        left, right, min_y, max_y = self._get_visible_bounds()

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
