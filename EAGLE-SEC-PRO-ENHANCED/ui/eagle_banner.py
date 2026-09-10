"""
EAGLE-SEC PRO — EagleBanner Widget
An animated cyberpunk header bar with a live mini eagle logo, 
pulsing status indicators, and scrolling threat ticker.
"""
import math
import random
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore    import Qt, QTimer, QPoint, QRect, QSize
from PyQt6.QtGui     import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QFont,
    QPen, QBrush, QPainterPath, QPolygon, QPixmap
)


class EagleBanner(QWidget):
    """
    Compact animated header strip:
      [Eagle Logo]  EAGLE-SEC PRO  v2.0     ● PROXY  ● SCANNER  ... [ticker]
    Height: 52px.
    """

    HEIGHT = 52

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self._angle      = 0.0
        self._frame      = 0
        self._ticker_x   = 0
        self._proxy_on   = False
        self._scan_pulse = 0.0

        # Ticker messages
        self._ticker_msgs = [
            "  ◈ EAGLE-SEC PRO  ◈  APEX PREDATOR EDITION  ◈  SECURE · FAST · LETHAL  ◈  ",
            "  ▶  HTTP/HTTPS INTERCEPT PROXY READY  ▶  DECODER · REPEATER · CRAWLER ARMED  ▶  ",
            "  ◈  PLUGIN SYSTEM ACTIVE  ◈  SESSION MANAGER ONLINE  ◈  CVE DATABASE LOADED  ◈  ",
        ]
        self._ticker_combined = "".join(self._ticker_msgs)
        self._ticker_char_w   = 7   # approximate px per char at font-size 9

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def set_proxy_status(self, active: bool):
        self._proxy_on = active

    def _tick(self):
        self._angle    = (self._angle + 1.2) % 360
        self._frame   += 1
        self._scan_pulse = math.sin(math.radians(self._angle * 3)) * 0.5 + 0.5
        # Advance ticker
        self._ticker_x -= 1
        total_w = len(self._ticker_combined) * self._ticker_char_w
        if self._ticker_x < -total_w:
            self._ticker_x = self.width()
        self.update()

    # ── Paint ──────────────────────────────────────────────────────────
    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.HEIGHT

        # Background
        bg = QLinearGradient(0, 0, 0, h)
        bg.setColorAt(0.0, QColor("#050f1e"))
        bg.setColorAt(0.5, QColor("#030c18"))
        bg.setColorAt(1.0, QColor("#020810"))
        p.fillRect(0, 0, w, h, bg)

        # Bottom border glow
        pulse = 0.5 + 0.5 * math.sin(math.radians(self._angle * 2))
        border_alpha = int(80 + 60 * pulse)
        grad_line = QLinearGradient(0, 0, w, 0)
        grad_line.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad_line.setColorAt(0.2, QColor(0, 200, 255, border_alpha))
        grad_line.setColorAt(0.5, QColor(0, 200, 255, border_alpha + 30))
        grad_line.setColorAt(0.8, QColor(0, 200, 255, border_alpha))
        grad_line.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(grad_line, 1))
        p.drawLine(0, h - 1, w, h - 1)

        # Eagle logo
        self._draw_mini_eagle(p, 28, h // 2)

        # Title text
        p.setPen(QColor("#00C8FF"))
        f = QFont("Consolas", 14, QFont.Weight.Bold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        p.setFont(f)
        p.drawText(58, 6, w - 58, 30, Qt.AlignmentFlag.AlignVCenter, "EAGLE-SEC PRO")

        # Version
        p.setPen(QColor(58, 88, 120))
        fv = QFont("Consolas", 8)
        fv.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(fv)
        p.drawText(58, 30, 120, 16, Qt.AlignmentFlag.AlignVCenter, "v2.0  APEX PREDATOR")

        # Status indicators
        self._draw_status_dots(p, 280, h // 2)

        # Scrolling ticker (right portion)
        ticker_start = 580
        ticker_w = w - ticker_start - 8
        if ticker_w > 40:
            p.setClipRect(ticker_start, 0, ticker_w, h)
            p.setPen(QColor(0, 200, 255, 55))
            ft = QFont("Consolas", 8)
            ft.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
            p.setFont(ft)
            p.drawText(ticker_start + self._ticker_x, h // 2 + 4, self._ticker_combined)
            p.setClipping(False)

            # Fade edges of ticker
            fade_l = QLinearGradient(ticker_start, 0, ticker_start + 30, 0)
            fade_l.setColorAt(0.0, QColor("#030c18"))
            fade_l.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.fillRect(ticker_start, 0, 30, h, fade_l)

            fade_r = QLinearGradient(w - 40, 0, w, 0)
            fade_r.setColorAt(0.0, QColor(0, 0, 0, 0))
            fade_r.setColorAt(1.0, QColor("#030c18"))
            p.fillRect(w - 40, 0, 40, h, fade_r)

        p.end()

    def _draw_mini_eagle(self, p: QPainter, cx: int, cy: int):
        """Tiny animated eagle head with rotating ring."""
        pulse = math.sin(math.radians(self._angle * 3)) * 0.5 + 0.5

        # Outer rotating ring
        ring_r = 18
        p.setPen(QPen(QColor(0, 200, 255, int(60 + 40 * pulse)), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        for i in range(12):
            a  = math.radians(self._angle + i * 30)
            r1 = ring_r - (5 if i % 3 == 0 else 3)
            x1 = cx + int(r1 * math.cos(a))
            y1 = cy + int(r1 * math.sin(a))
            x2 = cx + int(ring_r * math.cos(a))
            y2 = cy + int(ring_r * math.sin(a))
            alpha = 180 if i % 3 == 0 else 60
            p.setPen(QPen(QColor(0, 200, 255, alpha), 1))
            p.drawLine(x1, y1, x2, y2)

        # Head
        head_grad = QRadialGradient(cx - 2, cy - 2, 3)
        head_grad.setColorAt(0.0, QColor(0, 220, 255, 220))
        head_grad.setColorAt(1.0, QColor(0, 140, 200, 120))
        p.setBrush(head_grad)
        p.setPen(QPen(QColor(0, 200, 255), 1))
        p.drawEllipse(cx - 8, cy - 10, 16, 16)

        # Eye
        eye_a = int(200 + 55 * pulse)
        p.setBrush(QColor(255, 184, 0, eye_a))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx + 1, cy - 7, 5, 5)

        # Beak
        beak = QPolygon([
            QPoint(cx + 7, cy - 5),
            QPoint(cx + 13, cy - 7),
            QPoint(cx + 8, cy - 2),
        ])
        p.setBrush(QColor(255, 160, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(beak)

        # Mini wings
        p.setPen(QPen(QColor(0, 200, 255, int(80 + 40 * pulse)), 1))
        left_wing = QPolygon([
            QPoint(cx - 7, cy + 2), QPoint(cx - 16, cy - 4), QPoint(cx - 14, cy + 6)
        ])
        right_wing = QPolygon([
            QPoint(cx + 7, cy + 2), QPoint(cx + 16, cy - 4), QPoint(cx + 14, cy + 6)
        ])
        p.setBrush(QColor(0, 200, 255, 25))
        p.drawPolygon(left_wing)
        p.drawPolygon(right_wing)

    def _draw_status_dots(self, p: QPainter, x: int, cy: int):
        """Render small status pills for key subsystems."""
        statuses = [
            ("PROXY",   "#00FF99" if self._proxy_on else "#FF3355", self._proxy_on),
            ("SCAN",    "#00C8FF", True),
            ("DB",      "#00FF99", True),
            ("TLS",     "#00C8FF", True),
        ]

        font = QFont("Consolas", 8)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        p.setFont(font)

        dx = x
        for name, color_hex, active in statuses:
            col = QColor(color_hex)
            # Dot
            pulse_a = int(200 + 55 * self._scan_pulse) if active else 80
            p.setPen(Qt.PenStyle.NoPen)
            # Glow
            glow = QRadialGradient(dx + 5, cy, 7)
            glow.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 60 if active else 20))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.drawEllipse(dx - 2, cy - 9, 16, 16)
            # Dot fill
            p.setBrush(QColor(col.red(), col.green(), col.blue(), pulse_a if active else 60))
            p.drawEllipse(dx + 2, cy - 4, 7, 7)
            # Label
            p.setPen(QColor(col.red(), col.green(), col.blue(), 140 if active else 60))
            p.drawText(dx + 12, cy + 4, name)
            dx += 62
