import json, os
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "dictateflow" / "config.json"

DEFAULTS = {
    "widget_mode": "dictating",   # "always" | "dictating" | "hidden"
    "model_size":  "base.en",
    "trigger_key": "caps_lock",
}

def load():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
        except Exception:
            pass
    return dict(DEFAULTS)

def save(cfg):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
