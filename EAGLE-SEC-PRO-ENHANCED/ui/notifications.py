from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QColor


class NotificationToast(QWidget):
    COLORS = {
        "info":    ("#00D4FF", "#0d1b2e"),
        "success": ("#00FF88", "#0d1f16"),
        "warning": ("#FFB800", "#1f1a0d"),
        "error":   ("#FF4444", "#1f0d0d"),
    }

    def __init__(self, parent: QWidget, message: str, kind: str = "info", duration: int = 3000):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool |
                            Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        accent, bg = self.COLORS.get(kind, self.COLORS["info"])

        icons = {"info": "ℹ", "success": "✔", "warning": "⚠", "error": "✖"}

        self.setStyleSheet(f"""
            NotificationToast {{
                background: {bg};
                border: 1px solid {accent};
                border-radius: 8px;
                border-left: 3px solid {accent};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 16, 10)
        layout.setSpacing(10)

        icon = QLabel(icons.get(kind, "ℹ"))
        icon.setStyleSheet(f"color: {accent}; font-size: 16px;")
        layout.addWidget(icon)

        msg = QLabel(message)
        msg.setStyleSheet(f"color: #e2e8f0; font-size: 12px; font-family: Consolas;")
        msg.setWordWrap(True)
        msg.setMaximumWidth(320)
        layout.addWidget(msg)

        self.adjustSize()
        self._position()

        QTimer.singleShot(duration, self._dismiss)

    def _position(self):
        if self.parent():
            pw = self.parent()
            x = pw.width() - self.width() - 20
            y = pw.height() - self.height() - 60
            self.move(x, y)
        self.show()

    def _dismiss(self):
        self.hide()
        self.deleteLater()


class NotificationManager:
    def __init__(self, parent: QWidget):
        self._parent = parent
        self._queue: list[NotificationToast] = []
        self._enabled = True

    def show(self, message: str, kind: str = "info", duration: int = 3000):
        if not self._enabled:
            return
        toast = NotificationToast(self._parent, message, kind, duration)
        # Stack notifications
        offset = sum(t.height() + 8 for t in self._queue if not t.isHidden())
        if self._parent:
            x = self._parent.width() - toast.width() - 20
            y = self._parent.height() - toast.height() - 60 - offset
            toast.move(x, y)
        self._queue.append(toast)
        self._queue = [t for t in self._queue if not t.isHidden()]

    def info(self, msg: str): self.show(msg, "info")
    def success(self, msg: str): self.show(msg, "success")
    def warning(self, msg: str): self.show(msg, "warning")
    def error(self, msg: str): self.show(msg, "error")
    def set_enabled(self, v: bool): self._enabled = v
