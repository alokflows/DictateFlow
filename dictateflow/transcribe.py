"""Whisper transcription (runs in background thread)."""

import threading, tempfile, wave, os
import numpy as np

SAMPLE_RATE = 16000
_model      = None
_ready      = threading.Event()

def load_model(model_size="base.en"):
    global _model
    from faster_whisper import WhisperModel
    _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    _ready.set()

def is_ready():
    return _ready.is_set()

def transcribe(audio: np.ndarray, on_result):
    """Transcribe audio float32 array and call on_result(text)."""
    if not _ready.wait(timeout=60):
        return

    if len(audio) / SAMPLE_RATE < 0.4:
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name

    try:
        pcm = (audio * 32767).astype(np.int16)
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm.tobytes())

        segs, _ = _model.transcribe(tmp, language="en", vad_filter=True)
        text = " ".join(s.text.strip() for s in segs).strip()
        if text:
            on_result(text)
    finally:
        os.unlink(tmp)
