"""
DictateFlow widget — Whispr Flow-style minimal pill.
White background · thin border · 5 reactive black bars · nothing else.
"""

import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore    import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui     import QPainter, QColor, QPen, QBrush, QGuiApplication

# ── geometry ──────────────────────────────────────────────────────────────────
W, H          = 130, 36      # pill size
RADIUS        = H // 2       # fully rounded pill
MARGIN_BOTTOM = 52
N_BARS        = 5
BAR_W         = 3
BAR_GAP       = 5
BAR_MAX_H     = 18
BAR_MIN_H     = 3

# ── palette ──────────────────────────────────────────────────────────────────
C_BG          = QColor(255, 255, 255, 248)
C_BORDER      = QColor(30,  30,  30,  180)
C_BAR         = QColor(20,  20,  20)
C_BAR_IDLE    = QColor(180, 180, 180)
C_SPIN        = QColor(80,  80,  80,  200)


class DictateWidget(QWidget):

    def __init__(self, mode="dictating"):
        super().__init__()
        self._mode    = mode
        self._state   = "idle"     # idle | recording | processing
        self._bars    = [0.0] * N_BARS
        self._spin    = 0.0
        self._anim    = None
        self._drag    = None

        self._setup_window()
        QTimer(self).timeout.connect(self._tick)
        QTimer(self).setInterval(16)
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(16)

        if mode == "always":
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
        self.setFixedSize(W, H)
        self._park()

    def _park(self):
        scr = QGuiApplication.primaryScreen().geometry()
        self.move(scr.width() // 2 - W // 2, scr.height() + 20)

    def _on_screen_pos(self):
        scr = QGuiApplication.primaryScreen().geometry()
        return QPoint(scr.width() // 2 - W // 2,
                      scr.height() - H - MARGIN_BOTTOM)

    # ── slide animation ───────────────────────────────────────────────────────
    def _slide(self, target: QPoint, duration=180,
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

    def _appear(self):
        self.show()
        self._slide(self._on_screen_pos(), easing=QEasingCurve.Type.OutBack)

    def _disappear(self, then=None):
        scr = QGuiApplication.primaryScreen().geometry()
        target = QPoint(scr.width() // 2 - W // 2, scr.height() + 20)
        self._slide(target, duration=160, easing=QEasingCurve.Type.InCubic,
                    then=then)

    # ── public state API (called from main thread via Qt signals) ─────────────
    def show_recording(self):
        self._state = "recording"
        self._appear()

    def show_processing(self):
        self._state = "processing"
        self._bars  = [0.0] * N_BARS
        self.update()

    def hide_after_done(self):
        if self._mode == "always":
            self._state = "idle"
            self._bars  = [0.0] * N_BARS
            self.update()
        else:
            self._disappear(then=self._reset)

    def _reset(self):
        self._state = "idle"
        self._bars  = [0.0] * N_BARS
        self.hide()

    def set_bars(self, bars):
        # bars is N_BARS values 0–1 from audio.py
        self._bars = bars
        if self._state == "recording":
            self.update()

    # ── 60fps tick (spinner only) ─────────────────────────────────────────────
    def _tick(self):
        self._spin = (self._spin + 4.0) % 360.0
        if self._state == "processing":
            self.update()

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # White pill
        p.setPen(QPen(C_BORDER, 1.2))
        p.setBrush(QBrush(C_BG))
        p.drawRoundedRect(1, 1, W - 2, H - 2, RADIUS, RADIUS)

        cx, cy = W // 2, H // 2

        if self._state == "recording":
            self._paint_bars(p, cx, cy)
        elif self._state == "processing":
            self._paint_spinner(p, cx, cy)
        elif self._state == "idle":
            self._paint_idle_bars(p, cx, cy)

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

    def _paint_idle_bars(self, p, cx, cy):
        # In "always" mode — flat dim bars
        total = N_BARS * BAR_W + (N_BARS - 1) * BAR_GAP
        x0    = cx - total // 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(C_BAR_IDLE))
        for i in range(N_BARS):
            bx = x0 + i * (BAR_W + BAR_GAP)
            p.drawRoundedRect(bx, cy - 2, BAR_W, 4, 1, 1)

    def _paint_spinner(self, p, cx, cy):
        pen = QPen(C_SPIN, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = 9
        p.drawArc(cx - r, cy - r, r * 2, r * 2,
                  int(self._spin * 16), 250 * 16)

    # ── drag ─────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
