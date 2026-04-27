"""Audio recording and real-time FFT bar computation."""

import numpy as np
import sounddevice as sd
from collections import deque

SAMPLE_RATE = 16000
N_BARS      = 13
FFT_SIZE    = 1024

# Log-spaced frequency bands (80 Hz → 8 kHz), tuned for voice
_BANDS = np.logspace(np.log10(80), np.log10(8000), N_BARS + 1)

class AudioRecorder:
    def __init__(self, on_bars, on_chunk):
        self._on_bars  = on_bars    # callback(list[float])  — for UI
        self._on_chunk = on_chunk   # callback(np.ndarray)   — raw float32
        self._recording = False
        self._chunks    = []
        self._ring      = deque(maxlen=FFT_SIZE)
        self._bars      = [0.0] * N_BARS

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1,
            dtype="float32", blocksize=256,
            callback=self._cb
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):
        mono = indata[:, 0]
        self._ring.extend(mono)
        if self._recording:
            self._chunks.append(indata.copy())

        # FFT bar computation every callback
        if len(self._ring) == FFT_SIZE:
            self._compute_bars(np.array(self._ring))

    def _compute_bars(self, data):
        window  = data * np.hanning(len(data))
        fft_mag = np.abs(np.fft.rfft(window, n=FFT_SIZE))
        freqs   = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)

        new_bars = []
        for i in range(N_BARS):
            mask = (freqs >= _BANDS[i]) & (freqs < _BANDS[i + 1])
            val  = float(np.mean(fft_mag[mask])) if mask.any() else 0.0
            new_bars.append(val)

        # Normalise to 0–1
        peak = max(new_bars) or 1.0
        new_bars = [v / peak for v in new_bars]

        # Smooth: fast attack, slow decay
        for i in range(N_BARS):
            if new_bars[i] > self._bars[i]:
                self._bars[i] = self._bars[i] * 0.3 + new_bars[i] * 0.7
            else:
                self._bars[i] = self._bars[i] * 0.75 + new_bars[i] * 0.25

        self._on_bars(list(self._bars))

    def start_recording(self):
        self._chunks = []
        self._recording = True

    def stop_recording(self):
        self._recording = False
        if not self._chunks:
            return None
        return np.concatenate(self._chunks, axis=0).flatten()

    def close(self):
        self._stream.stop()
        self._stream.close()
