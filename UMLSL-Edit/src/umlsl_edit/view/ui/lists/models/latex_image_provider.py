"""
LaTeX image provider for QML views.

Provides a QQuickImageProvider that renders LaTeX strings to images
for display in QML list views.
"""

import logging
from collections import OrderedDict
from urllib.parse import unquote

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtQuick import QQuickImageProvider

from umlsl_edit.view.ui.lists.models.latex_renderer import latex_to_bytes

logger = logging.getLogger(__name__)


class LatexImageProvider(QQuickImageProvider):
    """
    Image provider that renders LaTeX strings to QML-compatible images.

    This provider is registered with the QML engine and can be accessed
    via image URLs in the format: "image://latex/<latex_string>"

    The LaTeX string in the URL should be URL-encoded if it contains
    special characters.
    """

    # A reasonable limit for UI elements in a list view.
    # 100 items prevents memory bloat while keeping scrolling smooth.
    CACHE_LIMIT = 100

    def __init__(self) -> None:
        """Initialize the LaTeX image provider."""
        super().__init__(QQuickImageProvider.ImageType.Pixmap)
        # OrderedDict allows us to implement an LRU (Least Recently Used) cache
        self._cache: OrderedDict[str, QPixmap] = OrderedDict()

    def requestPixmap(
            self, id: str, size: QSize, requestedSize: QSize
    ) -> QPixmap:
        """
        Provide a pixmap for the given LaTeX string.

        Args:
            id: The LaTeX string to render (URL-decoded by Qt).
            size: Output parameter for the actual image size.
            requestedSize: The requested size (width used as max_width if valid).

        Returns:
            The rendered pixmap.
        """
        # URL-decode the LaTeX string (Qt does not auto-decode image provider IDs)
        request_id = id
        latex_string = unquote(request_id)

        # Use requested size as max dimensions, or default to 200x36
        max_width = requestedSize.width() if requestedSize.width() > 0 else 200
        max_height = requestedSize.height() if requestedSize.height() > 0 else 36

        # Create a cache key based on the LaTeX and max dimensions
        cache_key = f"{latex_string}_{max_width}_{max_height}"

        # Use cached pixmap if available.
        if cache_key in self._cache:
            # Move to end to mark as recently used.
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        # Render if not cached.
        try:
            image_bytes = latex_to_bytes(
                latex_string,
                font_size=10,
                color="#FFFFFF",
            )
            pixmap = self._bytes_to_pixmap(image_bytes, max_width, max_height)
        except Exception as exc:
            logger.warning("Failed to render LaTeX image for '%s': %s", latex_string, exc, exc_info=True)
            pixmap = QPixmap()

        if pixmap.isNull():
            return QPixmap()

        # Cache rendered pixmap.
        self._cache[cache_key] = pixmap

        # Enforce cache limit with LRU eviction.
        if len(self._cache) > self.CACHE_LIMIT:
            # last=False pops from the beginning (the least recently used item).
            self._cache.popitem(last=False)

        return pixmap

    def _bytes_to_pixmap(
            self,
            image_bytes: bytes,
            max_width: int | None,
            max_height: int | None,
    ) -> QPixmap:
        """
        Convert image bytes to a QPixmap, scaled to fit within max dimensions.

        Args:
            image_bytes: The PNG image data.
            max_width: Maximum width. If None, no width limit.
            max_height: Maximum height. If None, no height limit.

        Returns:
            The scaled pixmap, or an empty pixmap on error.
        """
        if not image_bytes:
            return QPixmap()

        qimg = QImage.fromData(image_bytes)
        if qimg.isNull():
            return QPixmap()

        pixmap = QPixmap.fromImage(qimg)
        return self._scale_pixmap_to_fit(pixmap, max_width, max_height)

    def _scale_pixmap_to_fit(
            self,
            pixmap: QPixmap,
            max_width: int | None,
            max_height: int | None,
    ) -> QPixmap:
        """
        Scale a pixmap to fit within the given max dimensions while preserving aspect ratio.

        Only scales down if the pixmap exceeds the max dimensions. Does not scale up.

        Args:
            pixmap: The pixmap to scale.
            max_width: Maximum width. If None, no width limit.
            max_height: Maximum height. If None, no height limit.

        Returns:
            The scaled pixmap.
        """
        if pixmap.isNull():
            return pixmap

        current_width = pixmap.width()
        current_height = pixmap.height()

        # Calculate scale factors for each dimension
        width_scale = 1.0
        height_scale = 1.0

        if max_width is not None and current_width > max_width:
            width_scale = max_width / current_width

        if max_height is not None and current_height > max_height:
            height_scale = max_height / current_height

        # Use the smaller scale factor to ensure we fit within both constraints
        scale = min(width_scale, height_scale)

        if scale < 1.0:
            new_width = int(current_width * scale)
            new_height = int(current_height * scale)
            pixmap = pixmap.scaled(
                new_width,
                new_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        return pixmap

    def clear_cache(self) -> None:
        """Clear the image cache."""
        self._cache.clear()

    def invalidate_latex(self, latex: str) -> None:
        """
        Invalidate cached images for a specific LaTeX string.

        Args:
            latex: The LaTeX string whose cached images should be cleared.
        """
        # Create a list of keys first to avoid RuntimeErrors when modifying
        # the dictionary during iteration.
        keys_to_remove = [
            key for key in self._cache if key.startswith(f"{latex}_")
        ]
        for key in keys_to_remove:
            del self._cache[key]
