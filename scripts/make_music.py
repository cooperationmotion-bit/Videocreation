"""Original darkwave bed for the reel (synthesised from scratch, no samples).

100 BPM, A minor, 13 bars = 31.2 s. Cold drum machine, pulsing 16th saw bass,
detuned pad, gated-reverb snare, sparse lead. Bars 8-9 strip back to pad + bass
(the "relaxing is one part" moment) before the drums slam back in on bar 10.

Usage: python3 make_music.py out.wav
"""
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
BARS = 13
N = int(SR * BAR * BARS)
rng = np.random.default_rng(7)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def lp(x, fc, order=2):
    return sosfilt(butter(order, min(fc, SR / 2 - 100), "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((f * t + phase) % 1.0) - 1


def place(buf, x, start):
    i = int(start * SR)
    if i >= len(buf):
        return
    x = x[: len(buf) - i]
    buf[i : i + len(x)] += x


def reverb(x, secs=2.8, damp=3500, mix=0.35):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = lp(ir, damp)
    ir /= np.sqrt(np.sum(ir**2))
    wet = fftconvolve(x, ir)[: len(x)]
    return x * (1 - mix) + wet * mix * 1.6


# --- harmony: Am | F | G | Em (two bars each pass) -----------------------------
PROG = [57, 53, 55, 52]  # roots (A3 F3 G3 E3)
CHORDS = {57: [0, 3, 7], 53: [0, 4, 7], 55: [0, 4, 7], 52: [0, 3, 7]}


def root_at(bar):
    return PROG[(bar // 2) % 4] if bar < 12 else 57


# --- instruments ----------------------------------------------------------------
def kick():
    n = int(0.55 * SR)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    click = lp(rng.standard_normal(n), 3000) * np.exp(-t * 180) * 0.3
    return np.tanh((body + click) * 2.2) * 0.9


def snare():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    noise = bp(rng.standard_normal(n), 900, 7000) * np.exp(-t * 16)
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25) * 0.5
    return (noise + tone) * 0.55


def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7500, 4) * np.exp(-t * (14 if open_ else 70)) * 0.22


def bass_note(note, dur, bright):
    n = int(dur * SR)
    f = midi(note)
    x = saw(f, n) + 0.6 * saw(f * 1.004, n, 0.3) + 0.5 * np.sign(np.sin(2 * np.pi * f / 2 * np.arange(n) / SR))
    dark, hi = lp(x, 260), lp(x, 260 + 2200 * bright)
    t = np.arange(n) / SR
    fenv = np.exp(-t * 22)
    y = dark * (1 - fenv) + hi * fenv
    amp = np.minimum(1, t * 400) * np.exp(-t * 6)
    return np.tanh(y * amp * 1.4) * 0.32


def pad(notes, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for nt in notes:
        for d in (-0.09, 0, 0.11):
            x += saw(midi(nt) * 2 ** (d / 12), n, rng.random())
    sweep = 0.5 + 0.5 * np.sin(2 * np.pi * t / (dur * 2))
    x = lp(x, 900) * (1 - sweep) + lp(x, 1900) * sweep
    env = np.minimum(1, t / 0.6) * np.minimum(1, (dur - t) / 0.4).clip(0)
    return x * env * 0.045


def lead(note, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t * 3)
    ph = np.cumsum(midi(note) * vib) / SR
    x = 2 * (ph % 1) - 1 + 0.5 * np.sign(np.sin(2 * np.pi * ph))
    x = lp(x, 2400)
    env = np.minimum(1, t / 0.03) * np.exp(-t * 1.3)
    return x * env * 0.11


# --- arrangement ----------------------------------------------------------------
drums = np.zeros(N)
snares = np.zeros(N)
bass = np.zeros(N)
pads = np.zeros(N)
leads = np.zeros(N)
K, S = kick(), snare()

DRUM_BARS = set(range(2, 8)) | {10, 11}
BREAK_BARS = {8, 9}
for bar in range(BARS):
    b0 = bar * BAR
    r = root_at(bar)
    # pad (every two bars, sustained)
    if bar % 2 == 0 and bar < 12:
        pads_notes = [r + 12 + i for i in CHORDS[r]]
        place(pads, pad(pads_notes, 2 * BAR + 0.5), b0)
    if bar == 12:
        place(pads, pad([69, 72, 76], BAR * 1.3), b0)
    # drums
    if bar in DRUM_BARS:
        for beat in range(4):
            place(drums, K, b0 + beat * BEAT)
        for beat in (1, 3):
            place(snares, S, b0 + beat * BEAT)
        for e in range(8):
            place(drums, hat(open_=(e % 2 == 1 and e == 7)), b0 + e * BEAT / 2 + BEAT / 2 * 0.5 * (e % 2 == 0))
    elif bar == 1:
        for e in range(8):
            place(drums, hat() * (0.4 + e / 14), b0 + e * BEAT / 2)
    if bar == 12:
        place(drums, K, b0)
        place(snares, S * 1.2, b0)
    # bass: 16th pulse with octave hops, filtered more in intro/break
    if bar < 12:
        bright = 0.15 if bar == 0 else (0.25 if bar in BREAK_BARS else 0.7)
        vol = min(1.0, 0.25 + bar * 0.6) if bar < 2 else 1.0
        for s in range(16):
            octv = 12 if s in (3, 7, 11, 14) else 0
            place(bass, bass_note(r - 12 + octv, BEAT / 4 * 0.95, bright) * vol, b0 + s * BEAT / 4)
    if bar == 12:
        place(bass, bass_note(45, BAR, 0.3) * 1.2, b0)

# lead motif on bars 4-7 and 10-11
MOTIF = [(0, 76, 1.5), (1.5, 74, 0.5), (2, 72, 1.0), (3, 71, 1.0),
         (4, 72, 1.5), (5.5, 71, 0.5), (6, 69, 2.0)]
for start_bar in (4, 6, 10):
    for beat, note, d in MOTIF:
        place(leads, lead(note, d * BEAT * 1.4), start_bar * BAR + beat * BEAT)

# gated reverb on snare, big hall on pad/lead
gate_ir = lp(rng.standard_normal(int(0.3 * SR)), 6000) * np.linspace(1, 0.6, int(0.3 * SR))
gate_ir /= np.sqrt(np.sum(gate_ir**2))
snares = snares + fftconvolve(snares, gate_ir)[:N] * 0.5

# sidechain pump keyed off the kick grid (only where drums play)
t = np.arange(N) / SR
pump = np.ones(N)
for bar in DRUM_BARS:
    for beat in range(4):
        i0 = int((bar * BAR + beat * BEAT) * SR)
        n = int(BEAT * SR)
        env = 1 - 0.55 * np.exp(-np.arange(n) / SR * 9)
        pump[i0 : i0 + n] = np.minimum(pump[i0 : i0 + n], env)

music = (
    drums * 0.6
    + reverb(snares, 1.4, 5000, 0.3) * 1.1
    + bass * pump
    + reverb(pads, 3.5, 3000, 0.5) * pump * 1.4
    + reverb(leads, 3.0, 4000, 0.45) * 3.0
)
music = hp(music, 28)
# reverse swell into bar 2 (drop)
sw = np.zeros(N)
nsw = int(BAR * SR)
swell = hp(rng.standard_normal(nsw), 1500) * np.linspace(0, 1, nsw) ** 3 * 0.12
place(sw, swell, BAR)
place(sw, swell * 0.9, 9 * BAR)  # rise out of the break
music += reverb(sw, 1.5, 6000, 0.4)

# tail fade on the end card
fade = np.ones(N)
f0 = int((12 * BAR + 0.6) * SR)
fade[f0:] = np.linspace(1, 0, N - f0) ** 1.5
music *= fade
for name, stem in (("drums", drums), ("snare", snares), ("bass", bass), ("pad", pads), ("lead", leads)):
    print(f"{name:6s} rms {np.sqrt(np.mean(stem**2)):.3f}")
music /= np.max(np.abs(music))
music = np.tanh(music * 1.4)
music /= np.max(np.abs(music)) * 1.12

stereo = np.stack([music, np.roll(music, 220) * 0.98 + music * 0.02], axis=1)
wavfile.write(sys.argv[1], SR, (stereo * 32767).astype(np.int16))
print("wrote", sys.argv[1], N / SR, "s")
