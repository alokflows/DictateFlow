"""
DictateFlow — main application.
Wires together: key listener → audio → whisper → xdotool typing.
"""

import sys, threading, subprocess, time
import numpy as np

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore    import QObject, pyqtSignal, Qt
from PyQt6.QtGui     import QPainter, QColor, QPixmap, QIcon, QPen
from pynput          import keyboard as kb

from . import config, transcribe
from .audio  import AudioRecorder
from .widget import DictateWidget


# ── cross-thread signal bridge ────────────────────────────────────────────────
class _Bridge(QObject):
    show_recording  = pyqtSignal()
    show_processing = pyqtSignal()
    hide_done       = pyqtSignal()
    update_bars     = pyqtSignal(list)
    mode_changed    = pyqtSignal(str)

bridge = _Bridge()


# ── key listener ─────────────────────────────────────────────────────────────
_recording  = False
_press_time = 0.0
_recorder: AudioRecorder | None = None

def _on_press(key):
    global _recording, _press_time
    trigger = _get_trigger()
    if key == trigger and not _recording:
        _recording  = True
        _press_time = time.time()
        _recorder.start_recording()
        bridge.show_recording.emit()

def _on_release(key):
    global _recording
    trigger = _get_trigger()
    if key == trigger and _recording:
        _recording = False
        audio = _recorder.stop_recording()
        _reset_caps_if_needed(key)
        if audio is not None:
            bridge.show_processing.emit()
            threading.Thread(
                target=_do_transcribe, args=(audio,), daemon=True
            ).start()
        else:
            bridge.hide_done.emit()

def _do_transcribe(audio: np.ndarray):
    transcribe.transcribe(audio, on_result=_type_text)
    bridge.hide_done.emit()

def _type_text(text: str):
    time.sleep(0.06)
    subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

def _get_trigger():
    key_name = _cfg.get("trigger_key", "caps_lock")
    return getattr(kb.Key, key_name, kb.Key.caps_lock)

def _reset_caps_if_needed(key):
    if key == kb.Key.caps_lock:
        try:
            r = subprocess.run(["xset", "q"], capture_output=True, text=True)
            if "Caps Lock:   on" in r.stdout:
                subprocess.run(
                    ["xdotool", "key", "caps_lock"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception:
            pass


# ── tray icon ─────────────────────────────────────────────────────────────────
def _make_tray_pixmap(active=False):
    px = QPixmap(22, 22)
    px.fill(Qt.GlobalColor.transparent)
    p  = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    col = QColor(255, 59, 48) if active else QColor(180, 180, 190)
    p.setPen(QPen(col, 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(7, 1, 8, 12, 4, 4)
    p.drawArc(3, 9, 16, 10, 0, -180 * 16)
    p.drawLine(11, 19, 11, 21)
    p.drawLine(7, 21, 15, 21)
    p.end()
    return px


# ── main entry ────────────────────────────────────────────────────────────────
_cfg    = {}
_widget: DictateWidget | None = None

def run():
    global _cfg, _recorder, _widget

    _cfg = config.load()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Widget
    mode    = _cfg.get("widget_mode", "dictating")
    _widget = DictateWidget(mode=mode)

    # Wire signals
    bridge.show_recording.connect(_widget.show_recording)
    bridge.show_processing.connect(_widget.show_processing)
    bridge.hide_done.connect(_widget.hide_after_done)
    bridge.update_bars.connect(_widget.set_bars)

    # Audio recorder
    _recorder = AudioRecorder(
        on_bars  = lambda bars: bridge.update_bars.emit(bars),
        on_chunk = lambda _: None
    )

    # Load model in background
    model_size = _cfg.get("model_size", "base.en")
    threading.Thread(
        target=transcribe.load_model, args=(model_size,), daemon=True
    ).start()

    # Key listener
    listener = kb.Listener(on_press=_on_press, on_release=_on_release)
    listener.daemon = True
    listener.start()

    # System tray
    tray = QSystemTrayIcon(QIcon(_make_tray_pixmap()), app)
    tray.setToolTip("DictateFlow — hold Caps Lock to speak")

    menu = QMenu()

    # Mode submenu
    mode_menu = menu.addMenu("Widget")
    for label, value in [
        ("Show while dictating", "dictating"),
        ("Always visible",       "always"),
        ("Hidden",               "hidden"),
    ]:
        act = mode_menu.addAction(label)
        act.setCheckable(True)
        act.setChecked(_cfg.get("widget_mode") == value)
        act.triggered.connect(lambda _, v=value, a=act: _set_mode(v, menu, tray))

    menu.addSeparator()
    menu.addAction("Quit", app.quit)
    tray.setContextMenu(menu)
    tray.show()

    # Mode change handler
    def _set_mode(value, m, t):
        global _widget
        _cfg["widget_mode"] = value
        config.save(_cfg)
        # Rebuild widget with new mode
        _widget.hide()
        _widget.deleteLater()
        _widget = DictateWidget(mode=value)
        bridge.show_recording.disconnect()
        bridge.show_processing.disconnect()
        bridge.hide_done.disconnect()
        bridge.update_bars.disconnect()
        bridge.show_recording.connect(_widget.show_recording)
        bridge.show_processing.connect(_widget.show_processing)
        bridge.hide_done.connect(_widget.hide_after_done)
        bridge.update_bars.connect(_widget.set_bars)
        # Update checkmarks
        for action in m.actions():
            if hasattr(action, 'menu') and action.menu() == mode_menu_ref:
                pass

    mode_menu_ref = mode_menu

    sys.exit(app.exec())
