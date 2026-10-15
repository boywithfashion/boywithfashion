#!/usr/bin/env python3
"""Synthesize assets/sfx/paper-rip.wav: a paper tear matched to the torn-paper-rip visual.

The bundled SFX library has no tear, so this builds one from seeded noise: sparse fibre
crackles while the paper resists (first ~0.25 s, like the visual's slow start), then a dense,
bright rip as it gives way, then a short decay. Deterministic (fixed seed), mono 48 kHz.

    python3 tools/make_paper_rip.py
"""

import wave
from pathlib import Path

import numpy as np

SR = 48000
DUR = 0.95
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx" / "paper-rip.wav"


def bandpass(x, lo, hi):
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1 / SR)
    # Soft band: raised-cosine skirts so the band edges do not ring.
    gain = np.clip((freqs - lo * 0.6) / (lo * 0.4), 0, 1) * np.clip((hi * 1.4 - freqs) / (hi * 0.4), 0, 1)
    return np.fft.irfft(spec * gain, len(x))


def main():
    rng = np.random.default_rng(0x7A9E11CF)
    n = int(SR * DUR)
    t = np.arange(n) / SR

    # Crackle: many short decaying fibre snaps, sparse while resisting, dense once it gives.
    crackle = np.zeros(n)
    density = np.where(t < 0.25, 45, np.where(t < 0.7, 420, 90))  # snaps per second
    snap_len = int(0.004 * SR)
    snap_env = np.exp(-np.linspace(0, 6, snap_len))
    for i in range(0, n - snap_len, int(0.001 * SR)):
        if rng.random() < density[i] * 0.001:
            amp = rng.uniform(0.3, 1.0)
            crackle[i : i + snap_len] += amp * snap_env * rng.standard_normal(snap_len)

    # Body: the continuous tearing hiss under the snaps.
    body = rng.standard_normal(n)
    body_env = np.interp(t, [0, 0.2, 0.3, 0.62, 0.8, DUR], [0.05, 0.15, 0.9, 1.0, 0.25, 0])

    mix = bandpass(crackle, 1200, 7500) * 0.9 + bandpass(body, 900, 5000) * body_env * 0.45
    env = np.interp(t, [0, 0.02, 0.85, DUR], [0, 1, 0.6, 0])
    mix *= env
    mix /= np.max(np.abs(mix)) + 1e-9
    mix *= 0.89  # about -1 dBFS peak

    pcm = (mix * 32767).astype("<i2")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{OUT.relative_to(OUT.parent.parent.parent)} written ({DUR:.2f}s)")


if __name__ == "__main__":
    main()
