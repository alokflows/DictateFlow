"""
DictateFlow — main application wiring.

Hold trigger key  → hold-to-talk (release = type)
Quick tap (< 0.4s) → lock mode   (tap again or ✓ button = type, ● = cancel)
"""

import sys, threading, subprocess, time
import numpy as np

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtCore    import QObject, pyqtSignal, Qt
from PyQt6.QtGui     import QPainter, QColor, QPixmap, QIcon, QPen
from pynput          import keyboard as kb

from . import config, transcribe
from .audio           import AudioRecorder
from .widget          import DictateWidget
from .settings_dialog import SettingsDialog


# ── signal bridge ─────────────────────────────────────────────────────────────
class _Bridge(QObject):
    show_recording  = pyqtSignal()
    show_locked     = pyqtSignal()
    show_processing = pyqtSignal()
    hide_done       = pyqtSignal()
    update_bars     = pyqtSignal(list)
    open_settings   = pyqtSignal()

bridge = _Bridge()


# ── state ────────────────────────────────────────────────────────────────────
_state      = "idle"    # idle | holding | locked | processing
_press_time = 0.0
_recorder: AudioRecorder | None = None
_cfg: dict = {}
_audio_buffer: np.ndarray | None = None   # accumulated in lock mode


def _get_trigger():
    return getattr(kb.Key, _cfg.get("trigger_key", "caps_lock"), kb.Key.caps_lock)


def _on_press(key):
    global _state, _press_time
    if key != _get_trigger():
        return
    if _state == "idle":
        _press_time = time.time()
        _recorder.start_recording()
        _state = "holding"
        bridge.show_recording.emit()
    elif _state == "locked":
        # Second tap while locked → confirm
        _confirm()


def _on_release(key):
    global _state
    if key != _get_trigger():
        return
    if _state != "holding":
        return

    held = time.time() - _press_time
    _reset_caps(key)

    if held < 0.40:
        # Quick tap → switch to lock mode (keep recording)
        _state = "locked"
        bridge.show_locked.emit()
    else:
        # Normal hold-to-talk → transcribe immediately
        audio = _recorder.stop_recording()
        _state = "processing"
        bridge.show_processing.emit()
        threading.Thread(target=_do_transcribe, args=(audio,), daemon=True).start()


def _confirm():
    """Confirm lock-mode recording → transcribe + type."""
    global _state
    audio  = _recorder.stop_recording()
    _state = "processing"
    bridge.show_processing.emit()
    threading.Thread(target=_do_transcribe, args=(audio,), daemon=True).start()


def _cancel():
    """Cancel lock-mode recording without typing."""
    global _state
    _recorder.stop_recording()
    _state = "idle"
    bridge.hide_done.emit()


def _do_transcribe(audio):
    global _state
    if audio is not None:
        transcribe.transcribe(audio, on_result=_type_text)
    _state = "idle"
    bridge.hide_done.emit()


def _type_text(text: str):
    time.sleep(0.06)
    subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def _reset_caps(key):
    if key == kb.Key.caps_lock:
        try:
            r = subprocess.run(["xset", "q"], capture_output=True, text=True)
            if "Caps Lock:   on" in r.stdout:
                subprocess.run(["xdotool", "key", "caps_lock"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


# ── tray icon ─────────────────────────────────────────────────────────────────
def _tray_icon():
    px = QPixmap(22, 22)
    px.fill(Qt.GlobalColor.transparent)
    p  = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor(50, 50, 50), 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    # mic capsule
    p.drawRoundedRect(7, 1, 8, 12, 4, 4)
    # stand arc
    p.drawArc(3, 9, 16, 10, 0, -180 * 16)
    # pole + base
    p.drawLine(11, 19, 11, 21)
    p.drawLine(7, 21, 15, 21)
    p.end()
    return QIcon(px)


# ── settings ─────────────────────────────────────────────────────────────────
_widget: DictateWidget | None = None
_app:    QApplication  | None = None

def _open_settings():
    dlg = SettingsDialog(_cfg)
    if dlg.exec():
        new_cfg = dlg.get_config()
        _cfg.update(new_cfg)
        config.save(_cfg)
        _rebuild_widget()
        # Restart listener if key changed
        _restart_listener()
        # Notify model change needs restart
        if new_cfg.get("model_size") != _cfg.get("model_size"):
            QMessageBox.information(
                None, "DictateFlow",
                "Model change takes effect after restarting DictateFlow."
            )


def _rebuild_widget():
    global _widget
    if _widget:
        _widget.hide()
        _widget.deleteLater()
    _widget = _make_widget(_cfg.get("widget_mode", "dictating"))
    _wire_widget()


def _wire_widget():
    bridge.show_recording.connect(_widget.show_recording)
    bridge.show_locked.connect(_widget.show_locked)
    bridge.show_processing.connect(_widget.show_processing)
    bridge.hide_done.connect(_widget.hide_after_done)
    bridge.update_bars.connect(_widget.set_bars)


def _make_widget(mode):
    return DictateWidget(
        mode       = mode,
        on_confirm = _confirm,
        on_cancel  = _cancel,
    )


_listener = None

def _restart_listener():
    global _listener
    if _listener:
        _listener.stop()
    _listener = kb.Listener(on_press=_on_press, on_release=_on_release)
    _listener.daemon = True
    _listener.start()


# ── main ─────────────────────────────────────────────────────────────────────
def run():
    global _cfg, _recorder, _widget, _app

    _cfg = config.load()

    _app = QApplication(sys.argv)
    _app.setQuitOnLastWindowClosed(False)

    _widget = _make_widget(_cfg.get("widget_mode", "dictating"))
    _wire_widget()
    bridge.open_settings.connect(_open_settings)

    _recorder = AudioRecorder(
        on_bars=lambda bars: bridge.update_bars.emit(bars),
    )

    threading.Thread(
        target=transcribe.load_model,
        args=(_cfg.get("model_size", "base.en"),),
        daemon=True
    ).start()

    _restart_listener()

    # Tray
    tray = QSystemTrayIcon(_tray_icon(), _app)
    tray.setToolTip("DictateFlow")
    menu = QMenu()

    mode_menu = menu.addMenu("Widget")
    for label, value in [("Show while dictating","dictating"),
                         ("Always visible","always"),
                         ("Hidden","hidden")]:
        act = mode_menu.addAction(label)
        act.setCheckable(True)
        act.setChecked(_cfg.get("widget_mode") == value)
        def _set(checked, v=value):
            if not checked: return
            _cfg["widget_mode"] = v
            config.save(_cfg)
            _rebuild_widget()
        act.toggled.connect(_set)

    menu.addAction("Settings…", lambda: bridge.open_settings.emit())
    menu.addSeparator()
    menu.addAction("Quit", _app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(
        lambda r: bridge.open_settings.emit()
        if r == QSystemTrayIcon.ActivationReason.Trigger else None
    )
    tray.show()

    sys.exit(_app.exec())
