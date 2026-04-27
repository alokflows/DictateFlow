#!/usr/bin/env python3
"""Generate DictateFlow app icon — run once during install."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DISPLAY", ":0")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui     import (QPainter, QColor, QPixmap, QLinearGradient,
                              QPen, QPainterPath, QBrush)
from PyQt6.QtCore    import Qt

app = QApplication(sys.argv)

SZ = 512
px = QPixmap(SZ, SZ)
px.fill(Qt.GlobalColor.transparent)
p  = QPainter(px)
p.setRenderHint(QPainter.RenderHint.Antialiasing)

# Background — dark rounded square
bg_path = QPainterPath()
bg_path.addRoundedRect(0, 0, SZ, SZ, SZ * 0.22, SZ * 0.22)
grad = QLinearGradient(0, 0, 0, SZ)
grad.setColorAt(0.0, QColor(28, 28, 32))
grad.setColorAt(1.0, QColor(16, 16, 20))
p.fillPath(bg_path, QBrush(grad))

# Waveform bars — 5 white bars, symmetric heights
cx, cy = SZ // 2, SZ // 2
bar_w  = 42
bar_gap = 28
heights = [110, 200, 290, 200, 110]   # taller in centre
total_w = 5 * bar_w + 4 * bar_gap
x0 = cx - total_w // 2

p.setPen(Qt.PenStyle.NoPen)
for i, bh in enumerate(heights):
    bx = x0 + i * (bar_w + bar_gap)
    by = cy - bh // 2
    # White bar with slight transparency on edges
    alpha = 230 if i in (1, 2, 3) else 170
    p.setBrush(QBrush(QColor(255, 255, 255, alpha)))
    p.drawRoundedRect(bx, by, bar_w, bh, bar_w // 2, bar_w // 2)

p.end()

out = os.path.join(os.path.dirname(__file__), "assets", "icon.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
px.save(out)
print(f"Icon saved to {out}")
