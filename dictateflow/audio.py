"""Audio recording with spring-physics bar animation."""

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
N_BARS      = 5
FFT_SIZE    = 1024

_BANDS = np.logspace(np.log10(120), np.log10(7000), N_BARS + 1)

class AudioRecorder:
    def __init__(self, on_bars, on_chunk=None):
        self._on_bars  = on_bars
        self._recording = False
        self._chunks    = []
        self._ring      = np.zeros(FFT_SIZE, dtype=np.float32)
        self._ring_pos  = 0

        # Spring physics per bar: [position, velocity]
        self._phys = [[0.0, 0.0] for _ in range(N_BARS)]

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1,
            dtype="float32", blocksize=256,
            callback=self._cb
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):
        mono = indata[:, 0]
        # Fill ring buffer
        n = len(mono)
        end = (self._ring_pos + n) % FFT_SIZE
        if end > self._ring_pos:
            self._ring[self._ring_pos:end] = mono
        else:
            self._ring[self._ring_pos:] = mono[:FFT_SIZE - self._ring_pos]
            self._ring[:end] = mono[FFT_SIZE - self._ring_pos:]
        self._ring_pos = end

        if self._recording:
            self._chunks.append(indata.copy())

        self._update_bars()

    def _update_bars(self):
        window  = self._ring * np.hanning(FFT_SIZE)
        fft_mag = np.abs(np.fft.rfft(window, n=FFT_SIZE))
        freqs   = np.fft.rfftfreq(FFT_SIZE, 1.0 / SAMPLE_RATE)

        targets = []
        for i in range(N_BARS):
            mask = (freqs >= _BANDS[i]) & (freqs < _BANDS[i + 1])
            targets.append(float(np.mean(fft_mag[mask])) if mask.any() else 0.0)

        peak = max(targets) or 1.0
        targets = [min(v / peak, 1.0) for v in targets]

        # Spring physics: fast attack, slow natural decay
        for i, target in enumerate(targets):
            pos, vel = self._phys[i]
            force     = (target - pos) * (0.55 if target > pos else 0.18)
            vel       = vel * 0.72 + force
            pos       = max(0.0, min(1.0, pos + vel))
            self._phys[i] = [pos, vel]

        self._on_bars([p for p, _ in self._phys])

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
