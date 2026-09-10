"""
EAGLE-SEC PRO — APEX PREDATOR SPLASH SCREEN v2.0
3D-styled eagle with animated feathers, scanlines, particle system,
holographic grid, and cinematic load sequence.
"""
import math
import random
from PyQt6.QtWidgets import QSplashScreen
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QLinearGradient, QFont, QPen,
    QBrush, QRadialGradient, QPixmap, QPolygon, QConicalGradient,
    QPainterPath, QFontMetrics, QFontDatabase
)


# ── Colour palette ───────────────────────────────────────────────────
C_BG0     = QColor("#010610")
C_BG1     = QColor("#020c1e")
C_CYAN    = QColor("#00C8FF")
C_CYAN2   = QColor("#40e0ff")
C_GREEN   = QColor("#00FF99")
C_GOLD    = QColor("#FFB800")
C_RED     = QColor("#FF3355")
C_GRID    = QColor(13, 32, 52, 80)
C_SCAN    = QColor(0, 200, 255, 12)
C_MUTED   = QColor(58, 88, 120)
C_DARK    = QColor(4, 12, 24)


W, H = 760, 460


class Particle:
    """Floating ambient particle."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.x = random.uniform(0, W)
        self.y = random.uniform(0, H)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.6, -0.1)
        self.life = random.uniform(0.3, 1.0)
        self.decay = random.uniform(0.003, 0.008)
        self.size = random.uniform(1, 3)
        self.color_idx = random.randint(0, 2)  # 0=cyan,1=green,2=gold

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        if self.life <= 0 or self.y < -10:
            self.reset()


class SplashScreen(QSplashScreen):
    loading_complete = pyqtSignal()

    def __init__(self):
        pixmap = QPixmap(W, H)
        pixmap.fill(Qt.GlobalColor.transparent)
        super().__init__(
            pixmap,
            Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint
        )
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self._progress = 0
        self._status   = "INITIALIZING SYSTEMS..."
        self._angle    = 0.0       # animation angle (degrees)
        self._frame    = 0         # frame counter
        self._scanline = 0         # scanline position
        self._wing_flap = 0.0     # wing animation phase
        self._boot_phase = 0       # 0=dark, 1=reveal, 2=full
        self._reveal_alpha = 0     # fade-in

        # Particles
        self._particles = [Particle() for _ in range(55)]

        # Glitch state
        self._glitch_timer = 0
        self._glitch_active = False

        # Load sequence text lines for the boot log
        self._boot_lines: list[str] = []
        self._cursor_blink = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)   # ~60 fps

    # ── Tick ──────────────────────────────────────────────────────────
    def _tick(self):
        self._angle      = (self._angle + 1.8) % 360
        self._wing_flap  = (self._wing_flap + 0.045) % (2 * math.pi)
        self._scanline   = (self._scanline + 3) % H
        self._frame     += 1
        self._cursor_blink = (self._frame // 18) % 2 == 0

        # Fade in
        if self._reveal_alpha < 255:
            self._reveal_alpha = min(255, self._reveal_alpha + 6)

        # Glitch random
        self._glitch_timer += 1
        if self._glitch_timer > random.randint(80, 200):
            self._glitch_active = True
            self._glitch_timer  = 0
        if self._glitch_active and self._frame % 4 == 0:
            self._glitch_active = False

        # Particles
        for p in self._particles:
            p.update()

        self.repaint()

    # ── Progress ──────────────────────────────────────────────────────
    def set_progress(self, value: int, status: str = ""):
        self._progress = min(100, max(0, value))
        if status:
            self._status = status.upper()
            self._boot_lines.append(f"[{value:3d}%]  {status}")
            if len(self._boot_lines) > 5:
                self._boot_lines = self._boot_lines[-5:]
        self.repaint()

    # ── Main paint ────────────────────────────────────────────────────
    def drawContents(self, painter: QPainter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        self._draw_background(painter)
        self._draw_grid(painter)
        self._draw_particles(painter)
        self._draw_scanline(painter)
        self._draw_corner_brackets(painter)
        self._draw_side_data_panels(painter)
        self._draw_eagle_3d(painter, W // 2, 168)
        self._draw_title(painter)
        self._draw_boot_log(painter)
        self._draw_progress(painter)
        self._draw_status_line(painter)
        self._draw_border(painter)

        if self._glitch_active:
            self._draw_glitch(painter)

    # ── Background ────────────────────────────────────────────────────
    def _draw_background(self, p: QPainter):
        bg = QLinearGradient(0, 0, W, H)
        bg.setColorAt(0.0, QColor("#010610"))
        bg.setColorAt(0.4, QColor("#02091a"))
        bg.setColorAt(0.7, QColor("#010e1f"))
        bg.setColorAt(1.0, QColor("#010610"))
        p.fillRect(0, 0, W, H, bg)

        # Central vignette glow (eagle aura)
        rad = self._angle
        pulse = 0.85 + 0.15 * math.sin(math.radians(rad * 2))
        glow = QRadialGradient(W // 2, 158, int(220 * pulse))
        glow.setColorAt(0.0, QColor(0, 200, 255, int(22 * pulse)))
        glow.setColorAt(0.5, QColor(0, 200, 255, 6))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, W, H, glow)

        # Bottom glow strip
        bottom_glow = QLinearGradient(0, H - 80, 0, H)
        bottom_glow.setColorAt(0.0, QColor(0, 200, 255, 0))
        bottom_glow.setColorAt(1.0, QColor(0, 200, 255, 10))
        p.fillRect(0, H - 80, W, 80, bottom_glow)

    # ── Grid ──────────────────────────────────────────────────────────
    def _draw_grid(self, p: QPainter):
        p.setPen(QPen(C_GRID, 1))
        step = 36
        for x in range(0, W + step, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step):
            p.drawLine(0, y, W, y)

        # Perspective grid at bottom
        p.setPen(QPen(QColor(0, 200, 255, 18), 1))
        cx = W // 2
        gy = H - 10
        lines = 18
        for i in range(lines + 1):
            tx = int(W * i / lines)
            p.drawLine(cx, 260, tx, gy)
        for i in range(5):
            frac = i / 4
            yy = int(260 + (gy - 260) * frac)
            xl = int(cx - (cx) * frac * 0.9)
            xr = int(cx + (W - cx) * frac * 0.9)
            p.drawLine(xl, yy, xr, yy)

    # ── Scanline ──────────────────────────────────────────────────────
    def _draw_scanline(self, p: QPainter):
        # Moving bright scanline
        for dy in range(4):
            alpha = [40, 20, 10, 4][dy]
            p.setPen(QPen(QColor(0, 200, 255, alpha), 1))
            p.drawLine(0, self._scanline + dy, W, self._scanline + dy)

        # Static CRT scanlines (every 2 rows)
        p.setPen(QPen(QColor(0, 0, 0, 18), 1))
        for y in range(0, H, 2):
            p.drawLine(0, y, W, y)

    # ── Particles ─────────────────────────────────────────────────────
    def _draw_particles(self, p: QPainter):
        colors = [C_CYAN, C_GREEN, C_GOLD]
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._particles:
            col = colors[pt.color_idx]
            a = int(pt.life * 180)
            c = QColor(col.red(), col.green(), col.blue(), a)
            p.setBrush(c)
            size = int(pt.size * pt.life)
            if size >= 1:
                p.drawEllipse(int(pt.x), int(pt.y), size, size)

    # ── Corner brackets ───────────────────────────────────────────────
    def _draw_corner_brackets(self, p: QPainter):
        p.setPen(QPen(C_CYAN, 1))
        L = 22  # bracket length
        T = 3   # bracket thickness
        corners = [(2, 2), (W - 2 - L, 2), (2, H - 2 - L), (W - 2 - L, H - 2 - L)]
        for bx, by in corners:
            # horizontal
            p.fillRect(bx, by, L, T, C_CYAN)
            # vertical
            p.fillRect(bx, by, T, L, C_CYAN)

        # Thin inner frame
        p.setPen(QPen(QColor(0, 200, 255, 30), 1))
        p.drawRect(28, 28, W - 56, H - 56)

    # ── Side data panels ──────────────────────────────────────────────
    def _draw_side_data_panels(self, p: QPainter):
        font = QFont("Consolas", 7)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        p.setFont(font)

        left_data = [
            "SYS  ▶  ONLINE",
            "PROC ▶  ACTIVE",
            f"CLK  ▶  {self._frame:05d}",
            "NET  ▶  SECURE",
            "ENC  ▶  AES-256",
            "TLS  ▶  v1.3",
        ]
        right_data = [
            "INTERCEPT  ▶  READY",
            "PROXY      ▶  INIT",
            "SCANNER    ▶  ARMED",
            "CRAWLER    ▶  IDLE",
            "DB         ▶  OPEN",
            "PLUGINS    ▶  LOAD",
        ]

        p.setPen(QColor(0, 200, 255, 60))
        for i, line in enumerate(left_data):
            p.drawText(36, 52 + i * 15, line)

        p.setPen(QColor(0, 200, 255, 60))
        for i, line in enumerate(right_data):
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(line)
            p.drawText(W - 36 - tw, 52 + i * 15, line)

    # ── 3D Eagle ──────────────────────────────────────────────────────
    def _draw_eagle_3d(self, p: QPainter, cx: int, cy: int):
        """
        Render a pseudo-3D eagle using layered geometry, depth gradients,
        animated wing sweep, and glowing highlights.
        """
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        flap  = self._wing_flap
        pulse = math.sin(math.radians(self._angle * 2)) * 0.5 + 0.5

        # ── Eagle outer glow aura ──────────────────────────────────────
        aura_r = int(110 + 12 * pulse)
        aura = QRadialGradient(cx, cy, aura_r)
        aura.setColorAt(0.0, QColor(0, 200, 255, int(30 * pulse + 15)))
        aura.setColorAt(0.5, QColor(0, 200, 255, 8))
        aura.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(aura)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(cx - aura_r, cy - aura_r, aura_r * 2, aura_r * 2)

        # ── Shield body (3D gradient) ──────────────────────────────────
        def pt(x, y, ox=0, oy=0):
            return QPoint(int(cx + x + ox), int(cy + y + oy))

        # Shadow layer (depth illusion)
        shadow_shield = QPolygon([
            pt(-48, -72, 4, 5), pt(48, -72, 4, 5),
            pt(64, 4, 4, 5), pt(0, 70, 4, 5), pt(-64, 4, 4, 5)
        ])
        p.setBrush(QColor(0, 0, 0, 80))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPolygon(shadow_shield)

        # Main shield
        shield_path = QPainterPath()
        shield_path.moveTo(cx - 48, cy - 72)
        shield_path.lineTo(cx + 48, cy - 72)
        shield_path.cubicTo(cx + 68, cy - 50, cx + 68, cy - 20, cx + 60, cy + 4)
        shield_path.lineTo(cx, cy + 72)
        shield_path.lineTo(cx - 60, cy + 4)
        shield_path.cubicTo(cx - 68, cy - 20, cx - 68, cy - 50, cx - 48, cy - 72)
        shield_path.closeSubpath()

        shield_grad = QLinearGradient(cx - 48, cy - 72, cx + 48, cy + 72)
        shield_grad.setColorAt(0.0, QColor(8,  28, 52))
        shield_grad.setColorAt(0.3, QColor(5,  18, 36))
        shield_grad.setColorAt(0.7, QColor(3,  12, 24))
        shield_grad.setColorAt(1.0, QColor(2,   8, 16))
        p.setBrush(shield_grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(shield_path)

        # Shield edge highlight (left light source)
        edge_grad = QLinearGradient(cx - 48, cy, cx + 20, cy)
        edge_grad.setColorAt(0.0, QColor(0, 200, 255, 80))
        edge_grad.setColorAt(0.4, QColor(0, 200, 255, 25))
        edge_grad.setColorAt(1.0, QColor(0, 200, 255, 0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        edge_pen = QPen(edge_grad, 2.5)
        p.setPen(edge_pen)
        p.drawPath(shield_path)

        # Inner shield bevel
        bevel_path = QPainterPath()
        bevel_path.moveTo(cx - 34, cy - 56)
        bevel_path.lineTo(cx + 34, cy - 56)
        bevel_path.cubicTo(cx + 50, cy - 38, cx + 50, cy - 14, cx + 44, cy + 4)
        bevel_path.lineTo(cx, cy + 56)
        bevel_path.lineTo(cx - 44, cy + 4)
        bevel_path.cubicTo(cx - 50, cy - 14, cx - 50, cy - 38, cx - 34, cy - 56)
        bevel_path.closeSubpath()
        p.setPen(QPen(QColor(0, 200, 255, 28), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(bevel_path)

        # ── Wings ─────────────────────────────────────────────────────
        wing_sweep_y = int(math.sin(flap) * 14)
        wing_tip_y   = int(math.sin(flap) * 20)

        # Left wing layers (3D depth = three stacked polygons)
        for layer, (ox, oy, alpha) in enumerate([
            (0, 0,  255),   # top layer
            (3, 3,  120),   # mid shadow
            (5, 6,   50),   # deep shadow
        ]):
            left_wing = QPolygon([
                pt(-12,  -8 + wing_sweep_y, ox, oy),
                pt(-62, -38 + wing_sweep_y + 6, ox, oy),
                pt(-90, -22 + wing_tip_y, ox, oy),
                pt(-80,  10 + wing_tip_y, ox, oy),
                pt(-50,  18 + wing_tip_y, ox, oy),
                pt(-20,  10 + wing_sweep_y, ox, oy),
            ])
            right_wing = QPolygon([
                pt( 12,  -8 + wing_sweep_y, -ox, oy),
                pt( 62, -38 + wing_sweep_y + 6, -ox, oy),
                pt( 90, -22 + wing_tip_y, -ox, oy),
                pt( 80,  10 + wing_tip_y, -ox, oy),
                pt( 50,  18 + wing_tip_y, -ox, oy),
                pt( 20,  10 + wing_sweep_y, -ox, oy),
            ])

            if layer == 0:
                wing_grad_l = QLinearGradient(
                    cx - 90, cy - 38, cx - 12, cy + 18)
                wing_grad_l.setColorAt(0.0, QColor(0, 200, 255, 50))
                wing_grad_l.setColorAt(0.5, QColor(0, 160, 210, 35))
                wing_grad_l.setColorAt(1.0, QColor(0, 120, 180, 20))
                wing_grad_r = QLinearGradient(
                    cx + 12, cy - 38, cx + 90, cy + 18)
                wing_grad_r.setColorAt(0.0, QColor(0, 120, 180, 20))
                wing_grad_r.setColorAt(0.5, QColor(0, 160, 210, 35))
                wing_grad_r.setColorAt(1.0, QColor(0, 200, 255, 50))
                p.setBrush(wing_grad_l)
                p.setPen(QPen(QColor(0, 200, 255, 90), 1.5))
            else:
                a = alpha // 3
                p.setBrush(QColor(0, 0, 0, a))
                p.setPen(Qt.PenStyle.NoPen)

            p.drawPolygon(left_wing)

            if layer == 0:
                p.setBrush(wing_grad_r)
                p.setPen(QPen(QColor(0, 200, 255, 90), 1.5))
            p.drawPolygon(right_wing)

        # Wing feather detail lines
        p.setPen(QPen(QColor(0, 200, 255, 40), 1))
        for i in range(5):
            frac = (i + 1) / 6
            lx1 = cx - 12 - int(60 * frac)
            ly1 = cy - 8  + wing_sweep_y + int(frac * 16)
            lx2 = lx1 - 8
            ly2 = ly1 + 16 + wing_tip_y // 2
            p.drawLine(lx1, ly1, lx2, ly2)
            # Mirror
            p.drawLine(W - lx1, ly1, W - lx2, ly2)

        # ── Eagle body (torso) ─────────────────────────────────────────
        body_path = QPainterPath()
        body_path.moveTo(cx,      cy - 30)
        body_path.cubicTo(cx + 22, cy - 20, cx + 18, cy + 10, cx + 10, cy + 32)
        body_path.lineTo(cx,      cy + 46)
        body_path.lineTo(cx - 10, cy + 32)
        body_path.cubicTo(cx - 18, cy + 10, cx - 22, cy - 20, cx, cy - 30)
        body_path.closeSubpath()

        body_grad = QLinearGradient(cx - 22, cy - 30, cx + 22, cy + 46)
        body_grad.setColorAt(0.0, QColor(0, 200, 255, 120))
        body_grad.setColorAt(0.4, QColor(0, 180, 230, 80))
        body_grad.setColorAt(1.0, QColor(0, 120, 180, 50))
        p.setBrush(body_grad)
        p.setPen(QPen(C_CYAN, 1.5))
        p.drawPath(body_path)

        # Body highlight streak (3D lighting)
        streak = QPainterPath()
        streak.moveTo(cx - 4, cy - 28)
        streak.quadTo(cx - 8, cy + 5, cx - 5, cy + 30)
        p.setPen(QPen(QColor(255, 255, 255, 50), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(streak)

        # ── Head ──────────────────────────────────────────────────────
        # Head shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(cx - 13, cy - 66, 26, 26)

        # Head gradient
        head_grad = QRadialGradient(cx - 4, cy - 58, 4)
        head_grad.setColorAt(0.0, QColor(0, 220, 255, 220))
        head_grad.setColorAt(0.6, QColor(0, 180, 220, 160))
        head_grad.setColorAt(1.0, QColor(0, 120, 180, 100))
        p.setBrush(head_grad)
        p.setPen(QPen(C_CYAN, 1.5))
        p.drawEllipse(cx - 12, cy - 65, 24, 24)

        # Eye (gold)
        eye_pulse = int(255 * (0.7 + 0.3 * math.sin(math.radians(self._angle * 3))))
        p.setPen(Qt.PenStyle.NoPen)
        # Eye glow
        eye_glow = QRadialGradient(cx + 2, cy - 55, 8)
        eye_glow.setColorAt(0.0, QColor(255, 200, 0, eye_pulse))
        eye_glow.setColorAt(1.0, QColor(255, 160, 0, 0))
        p.setBrush(eye_glow)
        p.drawEllipse(cx - 4, cy - 61, 14, 14)
        # Eye pupil
        p.setBrush(QColor(255, 184, 0, eye_pulse))
        p.drawEllipse(cx + 1, cy - 58, 7, 7)
        # Eye highlight
        p.setBrush(QColor(255, 255, 200, 200))
        p.drawEllipse(cx + 4, cy - 56, 3, 3)

        # Beak (3D hooked)
        beak_path = QPainterPath()
        beak_path.moveTo(cx + 10, cy - 58)
        beak_path.cubicTo(cx + 22, cy - 60, cx + 24, cy - 52, cx + 14, cy - 48)
        beak_path.lineTo(cx + 8, cy - 52)
        beak_path.closeSubpath()
        beak_grad = QLinearGradient(cx + 8, cy - 60, cx + 24, cy - 48)
        beak_grad.setColorAt(0.0, QColor(255, 200, 0))
        beak_grad.setColorAt(1.0, QColor(200, 140, 0))
        p.setBrush(beak_grad)
        p.setPen(QPen(QColor(255, 160, 0), 1))
        p.drawPath(beak_path)

        # ── Talons ────────────────────────────────────────────────────
        talon_y = cy + 46
        for tx_off, direction in [(-12, -1), (12, 1)]:
            talon_path = QPainterPath()
            talon_path.moveTo(cx + tx_off, talon_y)
            for i in range(4):
                tangle = direction * (i * 25 - 30)
                tx = cx + tx_off + direction * int(14 * math.cos(math.radians(tangle)))
                ty = talon_y + int(14 * math.sin(math.radians(abs(tangle))) + 4)
                talon_path.lineTo(tx, ty)

            p.setPen(QPen(QColor(0, 200, 255, 160), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(talon_path)

        # ── Chest emblem (hex pattern) ─────────────────────────────────
        hex_cx, hex_cy = cx, cy + 8
        hex_r = 11
        hex_pts = QPolygon([
            QPoint(
                int(hex_cx + hex_r * math.cos(math.radians(a))),
                int(hex_cy + hex_r * math.sin(math.radians(a)))
            ) for a in range(0, 360, 60)
        ])
        p.setPen(QPen(QColor(0, 200, 255, 90), 1))
        p.setBrush(QColor(0, 200, 255, 15))
        p.drawPolygon(hex_pts)
        # Inner hex
        hex_r2 = 6
        hex_pts2 = QPolygon([
            QPoint(
                int(hex_cx + hex_r2 * math.cos(math.radians(a + 30))),
                int(hex_cy + hex_r2 * math.sin(math.radians(a + 30)))
            ) for a in range(0, 360, 60)
        ])
        p.setPen(QPen(QColor(0, 255, 153, 100), 1))
        p.setBrush(QColor(0, 255, 153, 20))
        p.drawPolygon(hex_pts2)

        # ── Rotating outer ring ────────────────────────────────────────
        ring_r = 88
        ring_pen = QPen(QColor(0, 200, 255, int(40 + 20 * pulse)), 1)
        p.setPen(ring_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        # Rotating tick marks on the ring
        p.setPen(QPen(C_CYAN, 1.5))
        for i in range(24):
            a  = math.radians(self._angle + i * 15)
            r1 = ring_r - (8 if i % 6 == 0 else 4)
            x1 = cx + int(r1 * math.cos(a))
            y1 = cy + int(r1 * math.sin(a))
            x2 = cx + int(ring_r * math.cos(a))
            y2 = cy + int(ring_r * math.sin(a))
            alpha = 180 if i % 6 == 0 else 70
            p.setPen(QPen(QColor(0, 200, 255, alpha), 1 if i % 6 else 2))
            p.drawLine(x1, y1, x2, y2)

        # Counter-rotating inner ring
        ring_r2 = 70
        p.setPen(QPen(QColor(0, 255, 153, int(25 + 15 * pulse)), 1))
        p.drawEllipse(cx - ring_r2, cy - ring_r2, ring_r2 * 2, ring_r2 * 2)

        p.restore()

    # ── Title text ────────────────────────────────────────────────────
    def _draw_title(self, p: QPainter):
        p.save()

        # Drop shadow
        p.setPen(QColor(0, 200, 255, 30))
        f_shadow = QFont("Consolas", 28, QFont.Weight.Bold)
        f_shadow.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 12)
        p.setFont(f_shadow)
        p.drawText(QRect(3, 283, W, 46), Qt.AlignmentFlag.AlignHCenter, "EAGLE-SEC PRO")

        # Main title with gradient simulation (draw twice: base + glow layer)
        p.setPen(C_CYAN)
        f_title = QFont("Consolas", 28, QFont.Weight.Bold)
        f_title.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 12)
        p.setFont(f_title)
        p.drawText(QRect(0, 280, W, 46), Qt.AlignmentFlag.AlignHCenter, "EAGLE-SEC PRO")

        # Glow overlay
        p.setPen(QColor(255, 255, 255, 40))
        f_glow = QFont("Consolas", 28, QFont.Weight.Bold)
        f_glow.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 12)
        p.setFont(f_glow)
        p.drawText(QRect(0, 280, W, 46), Qt.AlignmentFlag.AlignHCenter, "EAGLE-SEC PRO")

        # Subtitle
        p.setPen(QColor(58, 88, 120))
        f_sub = QFont("Consolas", 9)
        f_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        p.setFont(f_sub)
        p.drawText(QRect(0, 322, W, 22),
                   Qt.AlignmentFlag.AlignHCenter,
                   "PROFESSIONAL  WEB  SECURITY  TESTING  SUITE  ·  v2.0")

        # Divider
        grad_div = QLinearGradient(80, 0, W - 80, 0)
        grad_div.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad_div.setColorAt(0.3, QColor(0, 200, 255, 60))
        grad_div.setColorAt(0.5, QColor(0, 200, 255, 100))
        grad_div.setColorAt(0.7, QColor(0, 200, 255, 60))
        grad_div.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(grad_div, 1))
        p.drawLine(80, 347, W - 80, 347)

        p.restore()

    # ── Boot log ──────────────────────────────────────────────────────
    def _draw_boot_log(self, p: QPainter):
        if not self._boot_lines:
            return
        p.save()
        f = QFont("Consolas", 8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1)
        p.setFont(f)

        log_x = 48
        log_y_start = 354
        for i, line in enumerate(self._boot_lines[-3:]):
            alpha = [50, 90, 150][i] if len(self._boot_lines) >= 3 else 150
            p.setPen(QColor(0, 200, 255, alpha))
            cursor = "_" if (i == len(self._boot_lines[-3:]) - 1 and self._cursor_blink) else " "
            p.drawText(log_x, log_y_start + i * 13, f"▶  {line}{cursor}")

        p.restore()

    # ── Progress bar ──────────────────────────────────────────────────
    def _draw_progress(self, p: QPainter):
        p.save()
        bx, by, bw, bh = 48, 406, W - 96, 6
        br = 3  # radius

        # Track
        p.setBrush(QColor(4, 14, 28))
        p.setPen(QPen(QColor(13, 40, 64), 1))
        p.drawRoundedRect(bx, by, bw, bh, br, br)

        # Fill
        fill_w = int(bw * self._progress / 100)
        if fill_w > 0:
            fill_grad = QLinearGradient(bx, 0, bx + bw, 0)
            fill_grad.setColorAt(0.0, QColor("#006688"))
            fill_grad.setColorAt(0.4, QColor("#00C8FF"))
            fill_grad.setColorAt(0.7, QColor("#00C8FF"))
            fill_grad.setColorAt(1.0, QColor("#00FF99"))
            p.setBrush(fill_grad)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bx, by, fill_w, bh, br, br)

            # Shimmer
            shimmer_x = bx + int(fill_w * ((self._frame % 60) / 60))
            shimmer_grad = QLinearGradient(shimmer_x - 20, 0, shimmer_x + 20, 0)
            shimmer_grad.setColorAt(0.0, QColor(255, 255, 255, 0))
            shimmer_grad.setColorAt(0.5, QColor(255, 255, 255, 60))
            shimmer_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(shimmer_grad)
            clip_x = max(bx, min(shimmer_x - 20, bx + fill_w))
            clip_w = min(40, bx + fill_w - clip_x)
            if clip_w > 0:
                p.drawRoundedRect(clip_x, by, clip_w, bh, br, br)

        # Percentage text
        p.setPen(QColor(0, 200, 255, 160))
        f = QFont("Consolas", 8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(f)
        p.drawText(QRect(0, by + 10, W, 18), Qt.AlignmentFlag.AlignHCenter,
                   f"{self._progress}%  LOADED")

        p.restore()

    # ── Status line ───────────────────────────────────────────────────
    def _draw_status_line(self, p: QPainter):
        p.save()
        p.setPen(QColor(0, 200, 255, 90))
        f = QFont("Consolas", 8)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        p.setFont(f)
        p.drawText(QRect(0, 435, W, 16),
                   Qt.AlignmentFlag.AlignHCenter,
                   f"EAGLE-SEC PRO  ·  APEX PREDATOR EDITION  ·  SECURE · FAST · LETHAL")
        p.restore()

    # ── Outer border ──────────────────────────────────────────────────
    def _draw_border(self, p: QPainter):
        pulse = 0.5 + 0.5 * math.sin(math.radians(self._angle))
        a1 = int(100 + 60 * pulse)
        a2 = int(40 + 20 * pulse)

        # Outer glow border
        p.setPen(QPen(QColor(0, 200, 255, a1), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(1, 1, W - 2, H - 2)

        p.setPen(QPen(QColor(0, 200, 255, a2), 1))
        p.drawRect(3, 3, W - 6, H - 6)

    # ── Glitch ────────────────────────────────────────────────────────
    def _draw_glitch(self, p: QPainter):
        for _ in range(random.randint(2, 5)):
            gy = random.randint(0, H)
            gh = random.randint(2, 8)
            gx = random.randint(-20, 0)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 200, 255, random.randint(10, 35)))
            p.drawRect(gx, gy, W + 20, gh)

