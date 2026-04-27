"""Settings dialog — shortcut key picker + widget mode."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QPushButton, QFrame)
from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QFont, QColor
from . import config

KEYS = [
    ("Caps Lock",   "caps_lock"),
    ("Right Ctrl",  "ctrl_r"),
    ("Right Alt",   "alt_r"),
    ("Scroll Lock", "scroll_lock"),
    ("Pause/Break", "pause"),
]

MODES = [
    ("Show while dictating", "dictating"),
    ("Always visible",       "always"),
    ("Hidden",               "hidden"),
]

MODELS = [
    ("Tiny  — fastest, less accurate", "tiny.en"),
    ("Base  — balanced (default)",      "base.en"),
    ("Small — slower, more accurate",  "small.en"),
]


class SettingsDialog(QDialog):
    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = dict(cfg)
        self.setWindowTitle("DictateFlow Settings")
        self.setFixedSize(360, 280)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 24, 24, 20)

        title = QLabel("DictateFlow")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        title.setFont(f)
        root.addWidget(title)

        sub = QLabel("Settings")
        f2 = QFont(); f2.setPointSize(9)
        sub.setFont(f2)
        sub.setStyleSheet("color: #888;")
        root.addWidget(sub)

        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #ddd;")
        root.addWidget(line)

        # Trigger key
        root.addWidget(self._label("Trigger Key"))
        self._key_box = self._combo(KEYS, self._cfg.get("trigger_key", "caps_lock"))
        root.addWidget(self._key_box)

        # Widget mode
        root.addWidget(self._label("Widget Mode"))
        self._mode_box = self._combo(MODES, self._cfg.get("widget_mode", "dictating"))
        root.addWidget(self._mode_box)

        # Model
        root.addWidget(self._label("Whisper Model"))
        self._model_box = self._combo(MODELS, self._cfg.get("model_size", "base.en"))
        root.addWidget(self._model_box)

        root.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(
            "background:#1a1a1a; color:white; border-radius:6px;"
            "padding:6px 18px; font-weight:bold;"
        )
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _label(self, text):
        l = QLabel(text)
        f = QFont(); f.setPointSize(9); f.setBold(True)
        l.setFont(f)
        return l

    def _combo(self, items, current_value):
        box = QComboBox()
        box.setStyleSheet(
            "QComboBox { border:1px solid #ccc; border-radius:6px;"
            "padding:4px 8px; background:white; }"
        )
        for label, value in items:
            box.addItem(label, value)
        for i in range(box.count()):
            if box.itemData(i) == current_value:
                box.setCurrentIndex(i)
                break
        return box

    def _save(self):
        self._cfg["trigger_key"]  = self._key_box.currentData()
        self._cfg["widget_mode"]  = self._mode_box.currentData()
        self._cfg["model_size"]   = self._model_box.currentData()
        config.save(self._cfg)
        self.accept()

    def get_config(self):
        return self._cfg
