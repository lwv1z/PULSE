"""
visuals.py
Fully procedural 9:16 background — no stock footage / image APIs needed
(this sandbox can't reach Unsplash/Pexels/etc. anyway; this approach also
means zero licensing risk for the client). Dark gradient + slow diagonal
light sweep + a faint animated "growth line" motif that fits a finance
channel. Swap `palette` per-video for visual variety across a backlog.
"""
import numpy as np
from PIL import Image

W, H = 1080, 1920

PALETTES = [
    ((10, 14, 22), (16, 46, 40), (30, 130, 110)),   # dark teal/green (money)
    ((12, 10, 22), (36, 18, 54), (130, 70, 210)),   # violet
    ((8, 12, 20), (14, 30, 54), (40, 110, 220)),    # blue
]

# Render at quarter resolution and upscale — 4x less numpy work per frame,
# imperceptible on a soft animated gradient background.
RW, RH = W // 2, H // 2
_y_idx, _x_idx = np.mgrid[0:RH, 0:RW]
_diag = (_x_idx / RW + _y_idx / RH) / 2.0  # 0..1 diagonal ramp, precomputed once

# vignette is static (no t/palette dependence) — compute exactly once
_cy, _cx = RH * 0.55, RW * 0.5
_dist = np.sqrt(((_x_idx - _cx) / RW) ** 2 + ((_y_idx - _cy) / RH) ** 2)
_VIG = np.clip(1.0 - _dist * 0.9, 0.35, 1.0)[..., None]

_PALETTE_ARRAYS = [
    tuple(np.array(c, dtype=np.float32) for c in pal) for pal in PALETTES
]


def _lerp(a, b, t):
    return a + (b - a) * t


def render_background(t: float, duration: float, palette_idx: int = 0) -> Image.Image:
    c0, c1, c2 = _PALETTE_ARRAYS[palette_idx % len(_PALETTE_ARRAYS)]

    phase = (t / max(duration, 1)) * 0.6 + 0.15 * np.sin(t * 0.5)
    mix = np.clip(_diag + 0.25 * np.sin(_diag * 6.0 + t * 0.8), 0, 1)

    base = _lerp(c0, c1, mix[..., None])
    sweep = np.clip(1.0 - np.abs((mix - (phase % 1.0))) * 3.0, 0, 1)
    img = base + sweep[..., None] * (c2 - c1) * 0.5
    img = img * _VIG

    arr = np.clip(img, 0, 255).astype(np.uint8)
    small = Image.fromarray(arr, mode="RGB")
    return small.resize((W, H), Image.BILINEAR)
