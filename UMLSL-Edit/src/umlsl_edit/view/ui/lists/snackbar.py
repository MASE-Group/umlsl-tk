from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget


class GreenSnackbar(QWidget):
    """Transient snackbar widget for brief status messages."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Draw directly on the widget instead of using a QFrame container.
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 0, 16, 0)  # Bottom margin increased for shadow space
        self._layout.setSpacing(20)
        self.setMinimumWidth(150)
        self.setMinimumHeight(36)

        # Icon
        # self.icon_label = QLabel("✔")
        # self.icon_label.setStyleSheet("color: #011C27; font-size: 20px; font-weight: bold; background: transparent;")
        # self.layout.addWidget(self.icon_label)

        # Text
        self._text_label = QLabel("")
        self._text_label.setStyleSheet("color: #011C27; font-size: 13px; background: transparent;")
        self._layout.addWidget(self._text_label)

        # Single opacity effect to avoid stacked QGraphicsEffects.
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        # Animation
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.finished.connect(self.hide)

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

        self.hide()

    def paintEvent(self, event) -> None:
        """
        Custom paint to keep the pill and shadow consistent with opacity animation.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Leave space for the shadow.
        rect = self.rect().adjusted(2, 2, -2, -2)

        # Draw the pill background.
        painter.setBrush(QColor("#799582"))  # Sage Green
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 18, 18)

    def show_message(self, message: str = "", duration: int | None = 3000) -> None:
        """Show a snackbar message for the specified duration."""
        self._text_label.setText(message)
        self.adjustSize()

        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 8
            self.move(x, y)

        self._fade_animation.stop()
        self._opacity_effect.setOpacity(1.0)
        self.raise_()
        self.show()

        if duration is None or duration <= 0:
            self._timer.stop()
        else:
            self._timer.start(duration)

    def hide_message(self) -> None:
        """Fade the snackbar out immediately."""
        self._fade_out()

    def _fade_out(self) -> None:
        self._fade_animation.setDuration(500)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setEasingCurve(QEasingCurve.OutQuad)
        self._fade_animation.start()
