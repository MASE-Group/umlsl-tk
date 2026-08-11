"""
Canvas button controller for the UMLSL Traffic Editor.

Manages overlay buttons on the traffic canvas including zoom controls
and sidebar toggle functionality.
"""

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QFrame, QScrollArea, QToolButton

from umlsl_edit.view.ui.traffic_canvas.traffic_view import TrafficView
from umlsl_edit.view.view_constants import DIMENSION
from umlsl_edit.view.widgets.compiled_widgets.ui_main import Ui_MainWindow


class CanvasButtons(QObject):
    """
    Controller for canvas overlay buttons.

    Manages the zoom buttons and sidebar toggle button that float on top
    of the traffic view. Handles button positioning when the view is resized.

    Attributes:
        view: The traffic view widget that buttons overlay.
        zoom_buttons: Frame containing zoom in/out buttons.
        sidebar_toggle: Button for toggling sidebar visibility.
        sidebar: The sidebar scroll area to show/hide.
        zoom_in_button: Button for zooming in.
        zoom_out_button: Button for zooming out.
    """

    PADDING = 16

    def __init__(self, main_window: Ui_MainWindow) -> None:
        """
        Initialize the canvas buttons controller.

        Args:
            main_window: The main window instance containing the UI widgets.
        """
        super().__init__()
        self._window = main_window

        self._view: TrafficView = self._window.trafficView
        self._zoom_buttons: QFrame = self._window.zoom_buttons
        self._sidebar_toggle: QToolButton = self._window.b_sidebar_toggle
        self._sidebar: QScrollArea = self._window.sidebar
        self._zoom_in_button: QToolButton = self._window.b_plus
        self._zoom_out_button: QToolButton = self._window.b_minus

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up UI connections, reparent widgets, and install event filter."""
        self._reparent_overlay_widgets()
        self._connect_signals()
        self._view.installEventFilter(self)
        self._update_button_positions()

    def _reparent_overlay_widgets(self) -> None:
        """
        Reparent overlay widgets to the traffic view.

        This makes the buttons float on top of the canvas rather than
        being part of the main layout.
        """
        self._zoom_buttons.setParent(self._view)
        self._zoom_buttons.show()

        self._sidebar_toggle.setParent(self._view)
        self._sidebar_toggle.show()

    def _connect_signals(self) -> None:
        """Connect button click signals to their handlers."""
        self._zoom_in_button.clicked.connect(self._on_zoom_in)
        self._zoom_out_button.clicked.connect(self._on_zoom_out)
        self._sidebar_toggle.clicked.connect(self._toggle_sidebar)

    def _on_zoom_in(self) -> None:
        """Handle zoom in button click."""
        self._view.button_zoom(DIMENSION.BUTTON_ZOOM_AMOUNT)

    def _on_zoom_out(self) -> None:
        """Handle zoom out button click."""
        self._view.button_zoom(1 / DIMENSION.BUTTON_ZOOM_AMOUNT)

    def _toggle_sidebar(self) -> None:
        """Toggle the visibility of the sidebar panel."""
        self._sidebar.setVisible(not self._sidebar.isVisible())

    def _update_button_positions(self) -> None:
        """
        Update overlay button positions relative to the view.

        Positions the zoom buttons in the top-right corner and the
        sidebar toggle in the top-left corner.
        """
        zoom_x = self._view.width() - self._zoom_buttons.width() - self.PADDING
        self._zoom_buttons.move(zoom_x, self.PADDING)
        self._sidebar_toggle.move(0, self.PADDING)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """
        Filter events to update button positions on view resize.

        Args:
            source: The object that generated the event.
            event: The event being processed.

        Returns:
            False to allow normal event processing to continue.
        """
        if source == self._view and event.type() == QEvent.Type.Resize:
            self._update_button_positions()
        return super().eventFilter(source, event)
