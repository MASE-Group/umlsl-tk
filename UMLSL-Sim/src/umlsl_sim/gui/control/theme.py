"""Colour palette and metrics for the control GUI.

Colours mirror the UMLSL-Edit (PySide6) view constants so the two
tools look like one product:

    BACKGROUND #011C26   LAYER #032F40   TEXT #F9F9F9
    GREEN      #799582   RED   #D97855
"""
from __future__ import annotations

from typing import Tuple

RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


def _hex(code: str) -> RGB:
    code = code.lstrip("#")
    return int(code[0:2], 16), int(code[2:4], 16), int(code[4:6], 16)


def lighten(color: RGB, amount: float) -> RGB:
    """Blend ``color`` towards white by ``amount`` in [0, 1]."""
    return tuple(int(c + (255 - c) * amount) for c in color)  # type: ignore[return-value]


def darken(color: RGB, amount: float) -> RGB:
    """Blend ``color`` towards black by ``amount`` in [0, 1]."""
    return tuple(int(c * (1 - amount)) for c in color)  # type: ignore[return-value]


# --- Editor palette -------------------------------------------------------
BACKGROUND: RGB = _hex("#011C26")   # window / control-panel background
LAYER: RGB = _hex("#032F40")        # cards, dropdown faces, input fields
TEXT: RGB = _hex("#F9F9F9")
GREEN: RGB = _hex("#799582")        # positive actions (play / run)
RED: RGB = _hex("#D97855")          # destructive / stop / warnings

# --- Derived shades -------------------------------------------------------
LAYER_HOVER: RGB = lighten(LAYER, 0.12)
LAYER_ACTIVE: RGB = lighten(LAYER, 0.22)
BORDER: RGB = lighten(LAYER, 0.30)
MUTED_TEXT: RGB = darken(TEXT, 0.40)
DISABLED_TEXT: RGB = darken(TEXT, 0.62)
GREEN_HOVER: RGB = lighten(GREEN, 0.14)
RED_HOVER: RGB = lighten(RED, 0.14)
PANEL: RGB = darken(LAYER, 0.25)    # slightly darker than LAYER for the panel body

# Scene background matches the simulation's pale-green map colour.
SCENE_BG: RGB = (144, 215, 164)

# --- Metrics --------------------------------------------------------------
FONT = "Arial"
FONT_SIZE = 12
FONT_SIZE_SMALL = 10
FONT_SIZE_TITLE = 18

ROW_HEIGHT = 34
GAP = 10
PANEL_PAD = 16
PANEL_WIDTH = 340
CORNER = 6  # nominal corner radius (used only where segments are drawn)
