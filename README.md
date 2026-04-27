# DictateFlow

Apple-style voice dictation for Linux. Hold a key, speak, release — text appears instantly wherever your cursor is.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%28X11%29-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Minimal floating pill** — appears only while you're speaking, then vanishes
- **Real-time audio waveform** — bars react to actual FFT frequency content of your voice
- **Offline** — powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper); no API key, no internet needed
- **Types anywhere** — works in any app (browser, terminal, IDE, chat)
- **System tray** — right-click to switch modes or quit
- **Auto-starts** on login via systemd user service

## Widget modes

| Mode | Behaviour |
|------|-----------|
| **While dictating** *(default)* | Pill appears when you press Caps Lock, disappears after transcription |
| **Always visible** | Small dormant pill sits in corner; expands when you speak |
| **Hidden** | No UI at all — just works silently |

## Install

```bash
git clone https://github.com/alokflows/DictateFlow.git
cd DictateFlow
bash install.sh
```

## Usage

1. **Hold Caps Lock** and speak
2. **Release** — transcribed text is typed at your cursor
3. Right-click the **tray icon** to change mode or quit

## Requirements

- Ubuntu 22.04+ / Debian 12+ with X11 session
- Python 3.10+
- `ffmpeg`, `xdotool` (installed automatically)

## Configuration

Settings are saved to `~/.config/dictateflow/config.json`:

```json
{
  "widget_mode": "dictating",
  "model_size":  "base.en",
  "trigger_key": "caps_lock"
}
```

Available models: `tiny.en` (fastest), `base.en` (default), `small.en`, `medium.en` (most accurate).

## License

MIT
