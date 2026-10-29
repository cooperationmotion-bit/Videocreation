"""Composite graded segments + kinetic typography + music into the final reel.

Minimal / bold type after the reference: small Inter Display Bold caps, words split
either side of the subject, soft rise-in on the beat, cuts on the beat.

Usage: python3 compose.py <seg_dir> <music.wav> <out.mp4>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
BAR = 2.4
DUR = 13 * BAR
FONT_DIR = "/usr/share/fonts/opentype/inter/"
LIGHT = FONT_DIR + "InterDisplay-Light.otf"
MED = FONT_DIR + "Inter-Medium.otf"
INK = (242, 240, 235)
BG = (11, 11, 12)

seg_dir, music, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
SEGMENTS = sorted(seg_dir.glob("seg*.mp4"))

_fonts = {}


def font(path, size):
    key = (path, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def render_line(text, path, size, track=-0.012, color=INK):
    """Render one tracked line to an RGBA image (cached)."""
    f = font(path, size)
    adv = [f.getlength(c) + size * track for c in text]
    w = int(sum(adv) + size * 0.2)
    asc, desc = f.getmetrics()
    img = Image.new("RGBA", (w, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 0.0
    for c, a in zip(text, adv):
        d.text((x, 0), c, font=f, fill=color + (255,))
        x += a
    bbox = img.getbbox()
    return img.crop((0, bbox[1] - int(size * 0.04), bbox[2], bbox[3] + int(size * 0.04)))


_cache = {}


def line_img(text, path, size, track=-0.012, color=INK):
    key = (text, path, size, track, color)
    if key not in _cache:
        _cache[key] = render_line(text, path, size, track, color)
    return _cache[key]


def ease_out(p):
    p = min(max(p, 0.0), 1.0)
    return 1 - (1 - p) ** 4


def ease_in(p):
    p = min(max(p, 0.0), 1.0)
    return p**3


# Split-word layout after the reference: small bold words flanking the subject at a
# fixed height, left word left-aligned at XL, right word right-aligned at XR.
XL, XR = 150, 930  # XR keeps clear of the IG action rail
SIZE = 60
BOLD = FONT_DIR + "InterDisplay-Bold.otf"
L, R = "L", "R"

# (start, end, [(appear_t, text, side_or_x, y, font)])
CUES = [
    (0.35, 4.62, [(0.35, "FLEXIBILITY", 640, 820, BOLD), (2.4, "IS STRENGTH", 640, 900, BOLD)]),
    (4.8, 7.12, [(4.8, "MOBILITY", L, 1450, BOLD), (6.0, "+ STRENGTH", R, 1450, BOLD)]),
    (7.2, 9.42, [(7.2, "BUILDS", L, 1450, BOLD), (8.4, "CONTROL", R, 1450, BOLD)]),
    (9.6, 11.82, [(9.6, "OWN EVERY", 640, 820, BOLD), (10.8, "RANGE", 640, 900, BOLD)]),
    (12.0, 14.22, [(12.0, "STRONG", L, 1450, BOLD), (12.6, "AT LENGTH", R, 1450, BOLD)]),
    (14.4, 16.62, [(14.4, "STABLE", L, 1450, BOLD), (15.0, "AT END RANGE", R, 1450, BOLD)]),
    (16.8, 19.02, [(16.8, "LOAD", 640, 820, BOLD), (17.4, "THE RANGE", 640, 900, BOLD)]),
    # the break: music drops, type goes light: relaxing is one facet
    (19.35, 21.42, [(19.35, "RELAXING", L, 620, LIGHT), (20.0, "INTO IT", R, 620, LIGHT)]),
    (21.6, 23.82, [(21.6, "IS ONE", L, 1480, LIGHT), (22.2, "PART", R, 1480, LIGHT)]),
    (24.0, 26.22, [(24.0, "NOT THE", L, 960, BOLD), (24.6, "WHOLE PICTURE", R, 960, BOLD)]),
    (26.4, 27.52, [(26.4, "TRAIN IT", L, 1450, BOLD), (27.0, "LOAD IT", R, 1450, BOLD)]),
    (27.6, 28.72, [(27.6, "OWN IT", "C", 1450, BOLD)]),
]
REVEAL, EXIT, RISE = 0.32, 0.16, 14


def with_alpha(img, a):
    out = img.copy()
    out.putalpha(out.getchannel("A").point(lambda v: v * a // 255))
    return out


def draw_cue(frame, t, cue):
    start, end, lines = cue
    if not (start <= t < end + EXIT):
        return
    fade_out = 1 - ease_in((t - end) / EXIT) if t >= end else 1.0
    for at, txt, side, y, fp in lines:
        if t < at:
            continue
        img = line_img(txt, fp, SIZE, track=-0.02)
        p = ease_out((t - at) / REVEAL)
        a = int(255 * p * fade_out)
        if a <= 0:
            continue
        x = XL if side == L else XR - img.width if side == R else (W - img.width) // 2 if side == "C" else side
        frame.alpha_composite(with_alpha(img, a), (int(x), int(y - img.height / 2 + RISE * (1 - p))))


def end_card(t):
    """Bar 12: near-black card, one small bold line + tracked subtitle."""
    frame = Image.new("RGBA", (W, H), BG + (255,))
    lt = t - 12 * BAR
    main = line_img("MOBILITY × STRENGTH", BOLD, SIZE, track=-0.02)
    p = ease_out(lt / REVEAL)
    frame.alpha_composite(with_alpha(main, int(255 * p)),
                          ((W - main.width) // 2, int(H / 2 - main.height + RISE * (1 - p))))
    sub = line_img("FLEXIBILITY IS A STRENGTH SKILL", MED, 24, track=0.22)
    a = int(200 * ease_out((lt - 0.6) / 0.6))
    if a > 0:
        frame.alpha_composite(with_alpha(sub, a), ((W - sub.width) // 2, H // 2 + 30))
    return frame


# bottom gradient for legibility
grad = np.zeros((H, W, 4), np.uint8)
ramp = np.clip((np.arange(H) - 900) / (H - 900), 0, 1) ** 1.6
grad[..., 3] = (ramp * 70).astype(np.uint8)[:, None]
top = np.clip(1 - np.arange(H) / 380, 0, 1) ** 2

GRAD = Image.fromarray(grad, "RGBA")


def segment_frames():
    for seg in SEGMENTS:
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(seg), "-f", "rawvideo",
                              "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        frames = []
        while True:
            buf = p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                break
            frames.append(buf)
        p.wait()
        n = len(frames)
        for i, buf in enumerate(frames):
            yield i, n, buf


enc = subprocess.Popen([
    "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-i", music,
    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "14M", "-bufsize", "28M", "-pix_fmt", "yuv420p",
    "-profile:v", "high", "-movflags", "+faststart",
    "-c:a", "aac", "-b:a", "256k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000", "-ar", "48000",
    "-t", f"{DUR}", out], stdin=subprocess.PIPE)

fi = 0
src = segment_frames()
total = int(round(DUR * FPS))
while fi < total:
    t = fi / FPS
    if t < 12 * BAR:
        i, n, buf = next(src)
        img = Image.frombuffer("RGB", (W, H), buf)
        # slow push-in across each segment
        z = 1.0 + 0.045 * (i / max(n - 1, 1))
        cw, ch = W / z, H / z
        img = img.resize((W, H), Image.BICUBIC, box=((W - cw) / 2, (H - ch) * 0.45, (W + cw) / 2, (H - ch) * 0.45 + ch))
        frame = img.convert("RGBA")
        frame.alpha_composite(GRAD)
        for cue in CUES:
            draw_cue(frame, t, cue)
    else:
        frame = end_card(t)
    enc.stdin.write(frame.convert("RGB").tobytes())
    fi += 1
    if fi % 150 == 0:
        print(f"{fi}/{total}", flush=True)
enc.stdin.close()
enc.wait()
print("wrote", out)
