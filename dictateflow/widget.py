"""
DictateFlow pill widget.

Hold mode  : hold trigger key → bars animate → release → types
Lock mode  : quick-tap trigger key → bars animate → tap again or ✓ → types
                                                        or  ●  → cancel
"""

import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PyQt6.QtGui     import (QPainter, QColor, QPen, QBrush, QPainterPath,
                              QGuiApplication, QCursor)

# ── sizes ────────────────────────────────────────────────────────────────────
H             = 38
PILL_W_BARE   = 90      # hold mode  — just bars
PILL_W_LOCKED = 176     # lock mode  — ● bars ✓
RADIUS        = H // 2
MARGIN_BOTTOM = 52

N_BARS   = 5
BAR_W    = 8
BAR_GAP  = 5
BAR_MAX_H = 22
BAR_MIN_H  = 3

# ── palette ──────────────────────────────────────────────────────────────────
C_BG      = QColor(255, 255, 255, 250)
C_BORDER  = QColor(24,  24,  24,  190)
C_BAR     = QColor(18,  18,  18)
C_IDLE    = QColor(190, 190, 190)
C_CANCEL  = QColor(255, 59,  48)         # red  ●
C_CONFIRM = QColor(52,  199, 89)         # green ✓
C_SPIN    = QColor(90,  90,  90,  210)

BTN_R = (H - 12) // 2   # button radius
BTN_CY = H // 2
BTN_LEFT_CX  = 6 + BTN_R          # ● centre-x in locked pill
BTN_RIGHT_CX_OFFSET = 6 + BTN_R   # ✓ from right edge


class DictateWidget(QWidget):

    def __init__(self, mode="dictating", on_confirm=None, on_cancel=None):
        super().__init__()
        self._mode      = mode
        self._state     = "idle"      # idle|recording|locked|processing
        self._bars      = [0.0] * N_BARS
        self._spin      = 0.0
        self._anim      = None
        self._drag      = None
        self._on_confirm = on_confirm  # callable
        self._on_cancel  = on_cancel   # callable

        self._setup_window()
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(16)

        if mode == "always":
            self._set_width(PILL_W_BARE)
            self._appear()

    # ── window ────────────────────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(PILL_W_BARE, H)
        self._park()

    def _set_width(self, w):
        self.setFixedSize(w, H)

    def _park(self):
        scr = QGuiApplication.primaryScreen().geometry()
        self.move(scr.width() // 2 - self.width() // 2, scr.height() + 20)

    def _centre_pos(self, w=None):
        scr = QGuiApplication.primaryScreen().geometry()
        w   = w or self.width()
        return QPoint(scr.width() // 2 - w // 2,
                      scr.height() - H - MARGIN_BOTTOM)

    # ── animation ─────────────────────────────────────────────────────────────
    def _slide(self, target, duration=180,
               easing=QEasingCurve.Type.OutCubic, then=None):
        if self._anim:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(duration)
        self._anim.setEndValue(target)
        self._anim.setEasingCurve(easing)
        if then:
            self._anim.finished.connect(then)
        self._anim.start()

    def _appear(self, w=None):
        if w:
            self._set_width(w)
        self.show()
        self._slide(self._centre_pos(), easing=QEasingCurve.Type.OutBack,
                    duration=200)

    def _disappear(self, then=None):
        scr    = QGuiApplication.primaryScreen().geometry()
        target = QPoint(scr.width() // 2 - self.width() // 2,
                        scr.height() + 20)
        self._slide(target, duration=160,
                    easing=QEasingCurve.Type.InCubic, then=then)

    # ── public API ────────────────────────────────────────────────────────────
    def show_recording(self):
        self._state = "recording"
        self._appear(PILL_W_BARE)

    def show_locked(self):
        """Expand to locked pill with cancel / confirm buttons."""
        self._state = "locked"
        # Recentre with wider pill
        self._set_width(PILL_W_LOCKED)
        self.move(self._centre_pos(PILL_W_LOCKED))
        self.update()

    def show_processing(self):
        self._state = "processing"
        self._set_width(PILL_W_BARE)
        self.move(self._centre_pos(PILL_W_BARE))
        self._bars = [0.0] * N_BARS
        self.update()

    def hide_after_done(self):
        if self._mode == "always":
            self._state = "idle"
            self._bars  = [0.0] * N_BARS
            self._set_width(PILL_W_BARE)
            self.update()
        else:
            self._disappear(then=self._reset)

    def _reset(self):
        self._state = "idle"
        self._bars  = [0.0] * N_BARS
        self._set_width(PILL_W_BARE)
        self.hide()

    def set_bars(self, bars):
        self._bars = bars
        if self._state in ("recording", "locked"):
            self.update()

    # ── tick ─────────────────────────────────────────────────────────────────
    def _tick(self):
        self._spin = (self._spin + 4.5) % 360.0
        if self._state in ("processing", "idle"):
            self.update()

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W = self.width()

        # Pill background
        p.setPen(QPen(C_BORDER, 1.3))
        p.setBrush(QBrush(C_BG))
        p.drawRoundedRect(1, 1, W - 2, H - 2, RADIUS, RADIUS)

        cx, cy = W // 2, H // 2

        if self._state in ("recording", "locked"):
            self._paint_bars(p, cx, cy)
        if self._state == "locked":
            self._paint_buttons(p, W, cy)
        elif self._state == "processing":
            self._paint_spinner(p, cx, cy)
        elif self._state == "idle":
            self._paint_idle(p, cx, cy)

        p.end()

    def _paint_bars(self, p, cx, cy):
        total = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        x0    = cx - total // 2
        p.setPen(Qt.PenStyle.NoPen)
        for i, level in enumerate(self._bars):
            bh = max(BAR_MIN_H, int(level * BAR_MAX_H))
            bx = x0 + i * (BAR_W + BAR_GAP)
            by = cy - bh // 2
            p.setBrush(QBrush(C_BAR))
            p.drawRoundedRect(bx, by, BAR_W, bh, BAR_W // 2, BAR_W // 2)

    def _paint_buttons(self, p, W, cy):
        # ● cancel (left)
        lx = BTN_LEFT_CX
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(C_CANCEL))
        p.drawEllipse(lx - BTN_R, cy - BTN_R, BTN_R * 2, BTN_R * 2)

        # ✓ confirm (right)
        rx = W - BTN_RIGHT_CX_OFFSET - BTN_R
        p.setBrush(QBrush(C_CONFIRM))
        p.drawEllipse(rx, cy - BTN_R, BTN_R * 2, BTN_R * 2)

        # tick mark inside green circle
        tick = QPainterPath()
        cx_t = rx + BTN_R
        tick.moveTo(cx_t - 5, cy)
        tick.lineTo(cx_t - 1, cy + 4)
        tick.lineTo(cx_t + 6, cy - 5)
        pen = QPen(QColor(255, 255, 255), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.drawPath(tick)

    def _paint_spinner(self, p, cx, cy):
        pen = QPen(C_SPIN, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = 10
        p.drawArc(cx - r, cy - r, r * 2, r * 2,
                  int(self._spin * 16), 260 * 16)

    def _paint_idle(self, p, cx, cy):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(C_IDLE))
        total = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        x0    = cx - total // 2
        for i in range(N_BARS):
            p.drawRoundedRect(x0 + i * (BAR_W + BAR_GAP),
                              cy - 2, BAR_W, 4, 2, 2)

    # ── mouse (drag + button clicks) ──────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            lp = e.position()
            W  = self.width()
            if self._state == "locked":
                # ● cancel button
                if lp.x() < BTN_LEFT_CX + BTN_R + 6:
                    if self._on_cancel:
                        self._on_cancel()
                    return
                # ✓ confirm button
                if lp.x() > W - BTN_RIGHT_CX_OFFSET - BTN_R - 6:
                    if self._on_confirm:
                        self._on_confirm()
                    return
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
