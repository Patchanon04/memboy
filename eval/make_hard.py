"""Hard-mode variants of the generated receipts: realistic photo degradation, same ground truth.
Reads receipts/*.png -> writes receipts_hard/<same name> + copies labels.json."""
import io
import json
import math
import random
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC = Path(__file__).with_name("receipts")
OUT = Path(__file__).with_name("receipts_hard")
OUT.mkdir(exist_ok=True)


def perspective(im, rng, strength=0.12):
    """Tilted phone-photo look: random quad -> full rect."""
    w, h = im.size
    dx, dy = w * strength, h * strength
    quad = [rng.uniform(0, dx), rng.uniform(0, dy),                       # NW
            rng.uniform(0, dx), h - rng.uniform(0, dy),                   # SW
            w - rng.uniform(0, dx), h - rng.uniform(0, dy),               # SE
            w - rng.uniform(0, dx), rng.uniform(0, dy)]                   # NE
    return im.transform((w, h), Image.QUAD, quad, resample=Image.BICUBIC, fillcolor=(90, 85, 80))


def curl(im, rng):
    """Curved thermal paper: shift rows by a sine wave."""
    a = np.array(im)
    h, w = a.shape[:2]
    amp = rng.uniform(4, 12)
    phase = rng.uniform(0, math.pi)
    out = np.empty_like(a)
    for y in range(h):
        shift = int(amp * math.sin(math.pi * y / h + phase))
        out[y] = np.roll(a[y], shift, axis=0)
    return Image.fromarray(out)


def band_fade(im, rng):
    """Thermal print fading in horizontal bands (faint stripes of missing ink)."""
    a = np.array(im).astype(np.float32)
    h = a.shape[0]
    for _ in range(rng.randint(2, 4)):
        y0 = rng.randint(0, h - 30)
        bh = rng.randint(15, 60)
        fade = rng.uniform(0.35, 0.7)  # push toward white
        a[y0:y0 + bh] = a[y0:y0 + bh] * (1 - fade) + 255 * fade
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def hotspot(im, rng):
    """Uneven lighting: one bright flash spot + darker opposite corner."""
    w, h = im.size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = rng.uniform(0.2, 0.8) * w, rng.uniform(0.2, 0.8) * h
    d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / math.hypot(w, h)
    light = 1.25 - d * rng.uniform(0.5, 0.8)  # bright near spot, dim far away
    a = np.array(im).astype(np.float32) * light[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def motion_blur(im, rng):
    n = 5  # PIL only supports 3x3/5x5 kernels; run it twice for a longer streak
    k = [0.0] * (n * n)
    if rng.random() < 0.5:
        for i in range(n):
            k[(n // 2) * n + i] = 1 / n      # horizontal
    else:
        for i in range(n):
            k[i * n + n // 2] = 1 / n        # vertical
    f = ImageFilter.Kernel((n, n), k)
    return im.filter(f).filter(f)


def moire(im, rng):
    """Photo-of-a-screen: subtle diagonal scanline interference."""
    w, h = im.size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = rng.uniform(0, math.pi)
    period = rng.uniform(3, 6)
    wave = 12 * np.sin((x * math.cos(ang) + y * math.sin(ang)) * 2 * math.pi / period)
    a = np.array(im).astype(np.float32) + wave[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def finger(im, rng):
    """Fingertip occluding a corner."""
    w, h = im.size
    d = ImageDraw.Draw(im)
    r = int(min(w, h) * rng.uniform(0.12, 0.2))
    corner = rng.choice([(0, h), (w, h)])
    d.ellipse([corner[0] - r, corner[1] - r, corner[0] + r, corner[1] + r], fill=(224, 172, 138))
    return im


def crumple(im, rng):
    """Wrinkled paper: random low-freq displacement + creased shading."""
    a = np.array(im)
    h, w = a.shape[:2]
    gy, gx = np.mgrid[0:h, 0:w].astype(np.float32)
    for _ in range(rng.randint(2, 4)):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        amp, sigma = rng.uniform(3, 8), rng.uniform(40, 120)
        d2 = ((gx - cx) ** 2 + (gy - cy) ** 2) / (2 * sigma ** 2)
        gx += amp * np.exp(-d2) * rng.choice([-1, 1])
        gy += amp * np.exp(-d2) * rng.choice([-1, 1])
    xi = gx.clip(0, w - 1).astype(np.int32)
    yi = gy.clip(0, h - 1).astype(np.int32)
    warped = a[yi, xi]
    shade = np.ones((h, w), np.float32)
    for _ in range(rng.randint(3, 6)):  # crease lines
        x0, y0 = rng.randint(0, w), rng.randint(0, h)
        ang = rng.uniform(0, math.pi)
        dist = np.abs((gx - x0) * math.sin(ang) - (gy - y0) * math.cos(ang))
        shade *= 1 - 0.18 * np.exp(-(dist ** 2) / (2 * rng.uniform(2, 5) ** 2))
    out = (warped.astype(np.float32) * shade[..., None]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(out)


def cheap_camera(im, rng):
    """Downscale + heavy JPEG artifacts."""
    w, h = im.size
    s = rng.uniform(0.45, 0.65)
    im = im.resize((int(w * s), int(h * s)), Image.BILINEAR).resize((w, h), Image.BILINEAR)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=rng.randint(18, 35))
    return Image.open(buf).convert("RGB")


EFFECTS = [perspective, curl, band_fade, hotspot, motion_blur, moire, finger, crumple, cheap_camera]

random.seed(77)
for src in sorted(SRC.glob("[0-9]*.png")):
    rng = random.Random(src.name)  # ponytail: per-file seed -> reproducible set
    im = Image.open(src).convert("RGB")
    picks = rng.sample(EFFECTS, rng.randint(3, 5))
    if cheap_camera in picks:  # always last: artifacts should sit on top of everything
        picks.remove(cheap_camera)
        picks.append(cheap_camera)
    for fx in picks:
        im = fx(im, rng)
    im.save(OUT / src.name, quality=85)
    print(src.name, "->", "+".join(f.__name__ for f in picks))
shutil.copy(SRC / "labels.json", OUT / "labels.json")
print(f"done -> {OUT}")
