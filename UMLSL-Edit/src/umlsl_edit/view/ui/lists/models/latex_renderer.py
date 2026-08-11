"""
LaTeX rendering utilities for the UMLSL Traffic Editor.

Provides thread-safe LaTeX to image rendering using the Agg backend.
"""

import io
import logging

import matplotlib

# Force the non-interactive Agg backend BEFORE importing pyplot
# This is required for thread-safe rendering without GUI dependencies
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)


def latex_to_bytes(
        latex_str: str,
        font_size: int = 12,
        color: str = "black",
        dpi: int = 300,
) -> bytes:
    """
    Converts a LaTeX string into PNG image bytes using Matplotlib.

    This function is thread-safe and can be called from any thread because
    it uses the non-interactive Agg backend which doesn't require access
    to the GUI/main thread.

    Args:
        latex_str: The LaTeX string to render.
        font_size: Font size for the rendered text.
        color: Text color.
        dpi: Resolution of the output image.

    Returns:
        PNG image data as bytes, or empty bytes on error.
    """
    if not latex_str:
        return b""

    try:
        # Use the OO interface instead of pyplot for better thread safety
        fig = Figure(figsize=(0.1, 0.1), dpi=dpi)
        FigureCanvasAgg(fig)  # Attach canvas to figure for rendering

        # Wrap in $ for math mode if not already wrapped
        text_content = f"${latex_str}$" if not latex_str.startswith("$") else latex_str

        # Add text to figure
        fig.text(0, 0, text_content, fontsize=font_size, color=color)

        # Save to a memory buffer
        buf = io.BytesIO()
        fig.savefig(
            buf, format="png", bbox_inches="tight", pad_inches=0.05, transparent=True
        )
        plt.close(fig)  # Close figure to free memory

        buf.seek(0)
        return buf.getvalue()

    except Exception as e:
        logger.warning("Error rendering LaTeX: %s", e, exc_info=True)
        return b""
