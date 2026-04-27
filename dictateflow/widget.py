"""
DictateFlow floating widget — Apple-style minimal dictation pill.

States
------
idle        : hidden (dictating mode) or tiny dormant pill (always mode)
recording   : pill expands, waveform bars react to voice in real time
processing  : brief spinner while Whisper runs
"""

import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore    import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                              QRect, pyqtProperty, QPoint)
from PyQt6.QtGui     import (QPainter, QColor, QPen, QBrush, QPainterPath,
                              QLinearGradient, QGuiApplication)

# ── geometry ──────────────────────────────────────────────────────────────────
LIVE_W,  LIVE_H  = 240, 52    # pill while recording
IDLE_W,  IDLE_H  = 72,  36    # dormant pill in "always" mode
MARGIN_BOTTOM    = 48          # distance from screen bottom

# ── palette ──────────────────────────────────────────────────────────────────
C_BG       = QColor(16, 16, 18, 228)
C_BAR_MID  = QColor(255, 255, 255, 240)   # bright centre bars
C_BAR_EDGE = QColor(255, 255, 255, 110)   # dimmer side bars
C_DOT_REC  = QColor(255, 59,  48)         # Apple red
C_DOT_IDLE = QColor(120, 120, 130)
C_SPIN     = QColor(99,  179, 237, 200)

N_BARS = 13


class DictateWidget(QWidget):

    def __init__(self, mode="dictating"):
        super().__init__()
        self._mode       = mode        # "always" | "dictating" | "hidden"
        self._state      = "idle"      # "idle" | "recording" | "processing"
        self._bars       = [0.0] * N_BARS
        self._spin       = 0.0
        self._dot_pulse  = 0.0
        self._opacity    = 0.0         # 0.0 → 1.0 (paint opacity)

        self._setup_window()
        self._setup_timer()
        self._anim = None

        if mode == "always":
            self._show_idle()

    # ── window setup ─────────────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(LIVE_W, LIVE_H)
        self._park()           # move off-screen

    def _park(self):
        """Move widget below visible area (hidden position)."""
        screen = QGuiApplication.primaryScreen().geometry()
        self.move(screen.width() // 2 - LIVE_W // 2,
                  screen.height() + 10)

    def _center_bottom(self):
        screen = QGuiApplication.primaryScreen().geometry()
        return QPoint(
            screen.width() // 2 - LIVE_W // 2,
            screen.height() - LIVE_H - MARGIN_BOTTOM
        )

    # ── animation helpers ─────────────────────────────────────────────────────
    def _animate_to(self, target: QPoint, duration=220,
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

    # ── public state transitions ──────────────────────────────────────────────
    def show_recording(self):
        self._state   = "recording"
        self._opacity = 1.0
        self.show()
        self._animate_to(self._center_bottom(),
                         duration=200,
                         easing=QEasingCurve.Type.OutBack)

    def show_processing(self):
        self._state = "processing"
        self.update()

    def hide_after_done(self):
        if self._mode == "always":
            self._state = "idle"
            self._bars  = [0.0] * N_BARS
            self.update()
        else:
            # slide back down
            screen  = QGuiApplication.primaryScreen().geometry()
            parked  = QPoint(screen.width() // 2 - LIVE_W // 2,
                             screen.height() + 10)
            self._animate_to(parked, duration=180,
                             easing=QEasingCurve.Type.InCubic,
                             then=self._on_hidden)

    def _on_hidden(self):
        self._state = "idle"
        self._bars  = [0.0] * N_BARS
        self.hide()

    def _show_idle(self):
        """Only called in 'always' mode — show dormant pill."""
        self._state   = "idle"
        self._opacity = 1.0
        self.show()
        self._animate_to(self._center_bottom(), duration=250)

    # ── live bar feed (from audio thread) ─────────────────────────────────────
    def set_bars(self, bars):
        self._bars = bars
        # only repaint if visible and recording
        if self._state == "recording":
            self.update()

    # ── timer (60 fps spin / pulse) ───────────────────────────────────────────
    def _setup_timer(self):
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(16)

    def _tick(self):
        self._spin      = (self._spin + 3.5) % 360.0
        self._dot_pulse = (self._dot_pulse + 0.06) % (2 * math.pi)
        if self._state in ("processing", "idle"):
            self.update()

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H  = self.width(), self.height()
        cx, cy = W // 2, H // 2

        # Background pill
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(C_BG))
        p.drawRoundedRect(0, 0, W, H, H // 2, H // 2)

        if self._state == "recording":
            self._paint_recording(p, cx, cy, W, H)
        elif self._state == "processing":
            self._paint_processing(p, cx, cy, W, H)
        elif self._state == "idle":
            self._paint_idle(p, cx, cy, W, H)

        p.end()

    def _paint_recording(self, p, cx, cy, W, H):
        dot_r     = 6
        dot_x     = 22
        bar_area_w = W - dot_x * 2 - dot_r * 2 - 20
        bar_x0    = dot_x + dot_r + 10
        bar_max_h = H - 16
        bar_w     = max(3, (bar_area_w - (N_BARS - 1) * 3) // N_BARS)
        bar_gap   = 3

        # Waveform bars — colour gradient edge→centre→edge
        for i, level in enumerate(self._bars):
            t      = abs(i - (N_BARS - 1) / 2) / ((N_BARS - 1) / 2)  # 0=center,1=edge
            r      = int(C_BAR_EDGE.red()   + (C_BAR_MID.red()   - C_BAR_EDGE.red())   * (1 - t))
            g      = int(C_BAR_EDGE.green() + (C_BAR_MID.green() - C_BAR_EDGE.green()) * (1 - t))
            b_c    = int(C_BAR_EDGE.blue()  + (C_BAR_MID.blue()  - C_BAR_EDGE.blue())  * (1 - t))
            alpha  = int(C_BAR_EDGE.alpha() + (C_BAR_MID.alpha() - C_BAR_EDGE.alpha()) * (1 - t))
            col    = QColor(r, g, b_c, alpha)

            # Minimum height so bars are always visible
            bh     = max(4, int(level * bar_max_h))
            bx     = bar_x0 + i * (bar_w + bar_gap)
            by     = cy - bh // 2

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(col))
            p.drawRoundedRect(bx, by, bar_w, bh, bar_w // 2, bar_w // 2)

        # Red recording dot (pulsing)
        pulse = 0.85 + 0.15 * math.sin(self._dot_pulse)
        dr    = dot_r * pulse
        p.setBrush(QBrush(C_DOT_REC))
        p.drawEllipse(
            int(dot_x - dr), int(cy - dr),
            int(dr * 2),     int(dr * 2)
        )

    def _paint_processing(self, p, cx, cy, W, H):
        # Spinning arc
        pen = QPen(C_SPIN, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = 12
        p.drawArc(cx - r, cy - r, r * 2, r * 2,
                  int(self._spin * 16), 270 * 16)

    def _paint_idle(self, p, cx, cy, W, H):
        # Dim mic dot — just a tiny indicator
        pulse = 0.6 + 0.4 * math.sin(self._dot_pulse * 0.4)
        col   = QColor(int(C_DOT_IDLE.red()),
                       int(C_DOT_IDLE.green()),
                       int(C_DOT_IDLE.blue()),
                       int(80 * pulse))
        p.setBrush(QBrush(col))
        p.drawEllipse(cx - 4, cy - 4, 8, 8)

    # ── drag to reposition ────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if hasattr(self, "_drag") and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None
