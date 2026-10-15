#!/usr/bin/env python3
"""Synthesize assets/music/calm-bed.m4a: a soft, calm ambient bed for the reel.

Warm detuned pad on a slow Cmaj9 - Am9 - Fmaj9 - G(add9) loop at 72 BPM, a quiet sub
bass, and a gentle felt-piano style arpeggio for movement, through a synthetic room
reverb. Fully deterministic (fixed seed), stereo 48 kHz, loudness-normalized to
-22 LUFS so it sits well under the -14 LUFS voice.

    python3 tools/make_bgm.py [duration_seconds]
"""

import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 72
BAR = 4 * 60 / BPM  # one chord per bar, 3.33 s
TARGET_LUFS = -22.0
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "music" / "calm-bed.m4a"

# MIDI notes. Pad voicings sit around middle C; the arpeggio an octave up.
CHORDS = [
    {"bass": 36, "pad": [48, 55, 59, 62, 64], "arp": [72, 76, 79, 83, 86, 83, 79, 76]},  # Cmaj9
    {"bass": 45, "pad": [45, 52, 55, 59, 60], "arp": [69, 72, 76, 79, 83, 79, 76, 72]},  # Am9
    {"bass": 41, "pad": [41, 48, 52, 55, 57], "arp": [65, 69, 72, 76, 79, 76, 72, 69]},  # Fmaj9
    {"bass": 43, "pad": [43, 50, 55, 57, 59], "arp": [67, 71, 74, 79, 81, 79, 74, 71]},  # G(add9)
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cutoff):
    # FFT brick-ish lowpass with a soft roll-off; fast for the whole bed.
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec *= 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, len(x))


def render(duration):
    rng = np.random.default_rng(0x5EED)
    n = int(duration * SR)
    t = np.arange(n) / SR
    left = np.zeros(n)
    right = np.zeros(n)

    bars = int(np.ceil(duration / BAR)) + 1
    xfade = 1.2
    for b in range(bars):
        ch = CHORDS[b % len(CHORDS)]
        start = b * BAR - xfade / 2
        end = start + BAR + xfade
        i0, i1 = max(0, int(start * SR)), min(n, int(end * SR))
        if i0 >= i1:
            continue
        tt = t[i0:i1] - start
        span = end - start
        # raised-cosine in/out so chords melt into each other
        env = np.ones_like(tt)
        rise = tt < xfade
        env[rise] = 0.5 - 0.5 * np.cos(np.pi * tt[rise] / xfade)
        fall = tt > span - xfade
        env[fall] = 0.5 + 0.5 * np.cos(np.pi * (tt[fall] - (span - xfade)) / xfade)

        # Pad: two detuned voices per note, soft harmonic stack, slow vibrato.
        for k, m in enumerate(ch["pad"]):
            f0 = hz(m)
            for side, cents in ((left, -5), (right, 5)):
                f = f0 * 2 ** (cents / 1200)
                vib = 1 + 0.0015 * np.sin(2 * np.pi * (0.18 + 0.03 * k) * tt + k)
                phase = 2 * np.pi * f * np.cumsum(vib) / SR
                voice = sum(np.sin(h * phase + 0.7 * h) / h ** 1.6 for h in range(1, 7))
                side[i0:i1] += 0.055 * voice * env

        # Sub bass: root sine, very soft.
        fb = hz(ch["bass"])
        bass = np.sin(2 * np.pi * fb * tt) + 0.25 * np.sin(4 * np.pi * fb * tt)
        left[i0:i1] += 0.08 * bass * env
        right[i0:i1] += 0.08 * bass * env

        # Arpeggio: eighth notes, felt-piano pluck (fast attack, ~1.4 s decay).
        step = BAR / 8
        for s, m in enumerate(ch["arp"]):
            on = b * BAR + s * step
            j0 = int(on * SR)
            if j0 >= n or on < 0:
                continue
            ln = min(n - j0, int(2.2 * SR))
            tn = np.arange(ln) / SR
            f = hz(m)
            vel = 0.55 + 0.25 * rng.random()
            pluck = (np.sin(2 * np.pi * f * tn) + 0.3 * np.sin(4 * np.pi * f * tn) * np.exp(-tn * 4)) * np.exp(-tn * 2.4)
            pluck *= np.minimum(1, tn / 0.006) * vel * 0.05
            pan = 0.5 + 0.35 * np.sin(s * 1.3 + b)
            left[j0 : j0 + ln] += pluck * (1 - pan)
            right[j0 : j0 + ln] += pluck * pan

    left = lowpass(left, 2600)
    right = lowpass(right, 2600)

    # Room: convolve with a seeded, exponentially decaying noise tail.
    ir_len = int(2.4 * SR)
    ir_t = np.arange(ir_len) / SR
    for ch_i, sig in enumerate((left, right)):
        ir = rng.standard_normal(ir_len) * np.exp(-ir_t * 2.6)
        ir = lowpass(ir, 3500)
        ir /= np.sqrt(np.sum(ir**2))
        wet = np.fft.irfft(np.fft.rfft(sig, n + ir_len) * np.fft.rfft(ir, n + ir_len))[:n]
        mixed = 0.72 * sig + 0.45 * wet
        if ch_i == 0:
            left = mixed
        else:
            right = mixed

    fade_in, fade_out = 1.5, 2.0
    g = np.ones(n)
    g[t < fade_in] = (t[t < fade_in] / fade_in) ** 2
    tail = t > duration - fade_out
    g[tail] = ((duration - t[tail]) / fade_out) ** 2
    return np.stack([left * g, right * g], axis=1)


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def loudness(path):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    return float(json.loads(out[out.rindex("{") :])["input_i"])


def main():
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
    audio = render(duration)
    audio /= np.max(np.abs(audio)) + 1e-9
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "bed.wav"
        write_wav(raw, audio * 0.5)
        gain = 10 ** ((TARGET_LUFS - loudness(raw)) / 20)
        write_wav(raw, audio * 0.5 * gain)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:a", "aac", "-b:a", "160k", str(OUT)], check=True
        )
    print(f"{OUT.relative_to(ROOT)} written: {duration:.1f}s at {loudness(OUT):.1f} LUFS")


if __name__ == "__main__":
    main()
