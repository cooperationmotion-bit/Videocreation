"""Composite graded segments + kinetic typography + music into the final reel.

Minimal / bold editorial type: Inter Display Black, all caps, tight tracking,
mask-reveal (text rises from behind an invisible line), cuts on the beat.

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
BLACK = FONT_DIR + "InterDisplay-Black.otf"
LIGHT = FONT_DIR + "InterDisplay-Light.otf"
MED = FONT_DIR + "Inter-Medium.otf"
INK = (242, 240, 235)
BG = (11, 11, 12)
X0 = 84  # left margin
SAFE_BOTTOM = 1500  # keep clear of IG caption / buttons
MAX_W = W - X0 - 150  # right rail (like/comment/share) stays clear

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


# (start, end, [(appear_t, text, font, size)], anchor_y)  — anchor_y = baseline of last line
CUES = [
    (0.35, 4.62, [(0.35, "FLEXIBILITY", BLACK, 150), (2.4, "IS STRENGTH.", BLACK, 150)]),
    (4.8, 9.42, [(4.8, "MOBILITY", BLACK, 150), (6.0, "+ STRENGTH", BLACK, 150),
                 (8.4, "= CONTROL.", BLACK, 150)]),
    (9.6, 11.82, [(9.6, "OWN EVERY", BLACK, 150), (10.2, "RANGE.", BLACK, 150)]),
    (12.0, 14.22, [(12.0, "STRONG", BLACK, 160), (12.6, "AT LENGTH.", BLACK, 160)]),
    (14.4, 16.62, [(14.4, "STABLE", BLACK, 160), (15.0, "AT END RANGE.", BLACK, 118)]),
    (16.8, 19.02, [(16.8, "LOAD", BLACK, 160), (17.4, "THE RANGE.", BLACK, 160)]),
    # the break: music drops, type goes light — relaxing is one facet
    (19.35, 23.82, [(19.35, "RELAXING", LIGHT, 140), (20.0, "INTO A STRETCH", LIGHT, 112),
                    (21.6, "IS ONE PART.", LIGHT, 124)]),
    (24.0, 26.22, [(24.0, "NOT THE", BLACK, 150), (24.6, "WHOLE", BLACK, 150),
                   (25.2, "PICTURE.", BLACK, 150)]),
    (26.4, 28.72, [(26.4, "TRAIN IT.", BLACK, 150), (27.0, "LOAD IT.", BLACK, 150),
                   (27.6, "OWN IT.", BLACK, 150)]),
]
CHAPTERS = [(0, "01"), (4.8, "02"), (12.0, "03"), (16.8, "04"), (19.2, "05"), (24.0, "06")]
REVEAL, EXIT = 0.42, 0.2


def draw_cue(frame, t, cue):
    start, end, lines = cue
    if not (start <= t < end + EXIT):
        return
    imgs = [line_img(txt, fp, sz) for _, txt, fp, sz in lines]
    # auto-fit: keep the widest line clear of the IG action rail on the right
    widest = max(i.width for i in imgs)
    if widest > MAX_W:
        k = MAX_W / widest
        imgs = [line_img(txt, fp, int(sz * k)) for _, txt, fp, sz in lines]
    gap = 6
    total = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
    y = SAFE_BOTTOM - total
    exit_p = ease_in((t - end) / EXIT) if t >= end else 0.0
    for (at, *_), img in zip(lines, imgs):
        if t >= at:
            p = ease_out((t - at) / REVEAL)
            # mask reveal: rise from below the line's own box; exit continues upward
            dy = int(img.height * (1 - p)) - int(img.height * 1.05 * exit_p)
            if abs(dy) >= img.height:
                y += img.height + gap
                continue
            win = Image.new("RGBA", img.size, (0, 0, 0, 0))
            win.alpha_composite(img, (0, max(dy, 0)) if dy >= 0 else (0, 0),
                                (0, 0, img.width, img.height - dy) if dy >= 0 else (0, -dy, img.width, img.height))
            frame.alpha_composite(win, (X0 - 6, y))
        y += img.height + gap


def draw_chrome(frame, t):
    """Small tracked labels + hairline — the 'editorial' frame."""
    if t >= 12 * BAR:
        return
    d = ImageDraw.Draw(frame)
    lab = line_img("MOBILITY × STRENGTH", MED, 26, track=0.22, color=(242, 240, 235))
    a = int(200 * ease_out((t - 0.2) / 0.6))
    if a <= 0:
        return
    lab2 = lab.copy()
    lab2.putalpha(lab2.getchannel("A").point(lambda v: v * a // 255))
    frame.alpha_composite(lab2, (X0, 150))
    chap = [c for c in CHAPTERS if c[0] <= t][-1][1]
    num = line_img(f"{chap} / 06", MED, 26, track=0.18)
    num2 = num.copy()
    num2.putalpha(num2.getchannel("A").point(lambda v: v * a // 255))
    frame.alpha_composite(num2, (W - X0 - num.width, 150))
    # progress hairline
    prog = min(t / (12 * BAR), 1)
    y = 200
    d.line([(X0, y), (W - X0, y)], fill=(242, 240, 235, a // 4), width=2)
    d.line([(X0, y), (X0 + int((W - 2 * X0) * prog), y)], fill=(242, 240, 235, a), width=2)


def end_card(t):
    """Bar 12: black card, centred lock-up."""
    frame = Image.new("RGBA", (W, H), BG + (255,))
    lt = t - 12 * BAR
    lines = [("MOBILITY", BLACK, 150, 0.0), ("× STRENGTH", BLACK, 150, 0.25)]
    imgs = [line_img(a, b, c) for a, b, c, _ in lines]
    y = H // 2 - (imgs[0].height + imgs[1].height + 8) // 2 - 60
    for (_, _, _, at), img in zip(lines, imgs):
        p = ease_out((lt - at) / REVEAL)
        if p > 0:
            dy = int(img.height * (1 - p))
            if dy < img.height:
                win = Image.new("RGBA", img.size, (0, 0, 0, 0))
                win.alpha_composite(img, (0, dy), (0, 0, img.width, img.height - dy))
                frame.alpha_composite(win, ((W - img.width) // 2, y))
        y += img.height + 8
    sub = line_img("FLEXIBILITY IS A STRENGTH SKILL", MED, 28, track=0.2)
    a = int(255 * ease_out((lt - 0.7) / 0.6))
    if a > 0:
        s2 = sub.copy()
        s2.putalpha(s2.getchannel("A").point(lambda v: v * a // 255))
        frame.alpha_composite(s2, ((W - sub.width) // 2, y + 50))
    d = ImageDraw.Draw(frame)
    w = int(120 * ease_out((lt - 0.5) / 0.5))
    if w > 0:
        d.line([(W // 2 - w, y + 20), (W // 2 + w, y + 20)], fill=INK + (255,), width=3)
    return frame


# bottom gradient for legibility
grad = np.zeros((H, W, 4), np.uint8)
ramp = np.clip((np.arange(H) - 900) / (H - 900), 0, 1) ** 1.6
grad[..., 3] = (ramp * 175).astype(np.uint8)[:, None]
top = np.clip(1 - np.arange(H) / 380, 0, 1) ** 2
grad[..., 3] = np.maximum(grad[..., 3], (top * 110).astype(np.uint8)[:, None])
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
    "-c:a", "aac", "-b:a", "256k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
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
        draw_chrome(frame, t)
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
