"""
View constants for the UMLSL Traffic Editor.

This module contains all visual constants used throughout the view layer,
organized into logical groups for Z-ordering, dimensions, colors, and UI paths.
"""
from dataclasses import dataclass, field

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class _ZLayers:
    """Controls the drawing order (Z-Index) for scene items."""
    ROAD: int = 0
    SELECTED_ROAD: int = 1
    CROSSING: int = 2
    SELECTED_CROSSING: int = 3
    PATH: int = 4
    SEGMENT_INTERVAL: int = 5
    CAR: int = 6
    SELECTED_CAR: int = 7
    OVERLAY: int = 100


@dataclass(frozen=True)
class _Dimension:
    """Physical dimensions and rendering scales."""
    # Lane and car dimensions (in scene units)
    LANE_WIDTH: float = 1.0

    CAR_WIDTH: float = 0.6
    CAR_TRIANGLE_LENGTH: float = 0.4

    # Scene configuration
    SCENE_SIZE: int = 40

    # Zoom constraints
    MAX_ZOOM: float = 100.0
    MIN_ZOOM: float = 3.0
    INITIAL_ZOOM: float = 40.0
    BUTTON_ZOOM_AMOUNT: float = 1.4

    # Zoom thresholds for detail levels
    LANE_LABEL_MIN_ZOOM: float = 0
    GRID_FINE_THRESHOLD: float = 20.0

    # Grid spacing
    GRID_STEP_COARSE: float = 10.0
    GRID_STEP_FINE: float = 1.0

    # Line widths
    LINE_WIDTH_ROAD_DIVIDER: float = 0.05
    LINE_WIDTH_CROSSING_SEGMENT: float = 0.02

    # Zoom sensitivity
    TOUCHPAD_ZOOM_SENSITIVITY: float = 0.01
    WHEEL_ZOOM_SENSITIVITY: float = 0.001

    # Label drawing
    LABEL_PADDING: int = 5


@dataclass(frozen=True)
class _Colors:
    """Standard UI colors for the traffic editor."""
    # Background colors
    BACKGROUND: QColor = field(default_factory=lambda: QColor("#011C26"))
    LAYER: QColor = field(default_factory=lambda: QColor("#032F40"))

    # Text and UI elements
    TEXT: QColor = field(default_factory=lambda: QColor("#F9F9F9"))

    # Status colors
    GREEN: QColor = field(default_factory=lambda: QColor("#799582"))
    RED: QColor = field(default_factory=lambda: QColor("#D97855"))

    # Utility
    TRANSPARENT: QColor = field(default_factory=lambda: QColor(0, 0, 0, 0))

    CAR_COLORS  = [
        (128, 0, 0),
        (154, 99, 36),
        (128, 128, 0),
        (70, 153, 144),
        (0, 0, 117),
        (0, 0, 0),
        (230, 25, 76),
        (245, 130, 49),
        (255, 224, 25),
        (191, 239, 69),
        (60, 180, 75),
        (66, 212, 244),
        (67, 99, 216),
        (145, 30, 180),
        (240, 50, 230),
        (169, 169, 169),
        (250, 190, 212),
        (255, 216, 177),
        (255, 250, 200),
        (170, 255, 195),
        (220, 190, 255),
        (255, 255, 255),
    ]


@dataclass(frozen=True)
class _UIPaths:
    """Paths to UI resource files (relative to the widgets folder)."""
    MAIN_WINDOW: str = "../widgets/main.compiled_widgets"
    LIST_ITEM: str = "compiled_widgets/list.compiled_widgets"
    CAR_EDIT: str = "../widgets/car_edit.compiled_widgets"


# --- Public Singleton Instances ---
Z_LAYERS = _ZLayers()
DIMENSION = _Dimension()
COLORS = _Colors()
UI_PATHS = _UIPaths()
