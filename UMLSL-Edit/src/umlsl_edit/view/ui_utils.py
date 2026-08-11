"""
UI utility functions for the UMLSL Traffic Editor.

Provides helper functions for loading Qt Designer UI files.
"""
import logging
from typing import Optional

from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


def load_ui(path: str, parent: Optional[QWidget] = None) -> Optional[QWidget]:
    """
    Load a Qt Designer UI file and return the corresponding widget.

    Args:
        path: Path to the .ui file to load.
        parent: Optional parent widget for the loaded UI.

    Returns:
        The loaded QWidget, or None if loading failed.
    """
    loader = QUiLoader()
    file = QFile(path)

    if not file.open(QFile.ReadOnly):
        logger.error("Could not open UI file: %s", path)
        return None

    widget = loader.load(file, parent)
    file.close()
    return widget
