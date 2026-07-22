"""Creature archetypes (dec-0022): parametric recipes, not per-name builders.

`blob` is the first — a slime/ooze/jelly is `blob(color=..., size=..., eyes=...)`,
not hand-drawn each time. Built to the sprite standard (dec-0021): one material ramp
(shadow cool / base / highlight warm), directional top-left light, selective outline,
a readable rounded silhouette. This is the "easier/better way to make slimes".
"""
from __future__ import annotations

import numpy as np

from .shading import Ramp
from .sprite import Canvas, outline_dark

BLOB_DEFAULT = {"color": (96, 200, 96), "size": "m", "eyes": 2}
_SIZE = {"s": (6, 9), "m": (8, 11), "l": (10, 13)}   # (ry, rx)


def build_blob(contract, config=None) -> np.ndarray:
    cfg = {**BLOB_DEFAULT, **(config or {})}
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")               # 32x32
    cv = Canvas(w, h)
    cx = w // 2
    ry, rx = _SIZE.get(cfg["size"], _SIZE["m"])
    cy = h - ry - 2                                   # sit near the ground

    # --- silhouette + directional form shadow (light top-left) ---
    # shadow dome underneath; base dome shifted 1px up-left leaves a thin shadow
    # rim on the bottom-right — clean form shading, not a pillow blob.
    cv.disc(cy, cx, ry, rx, body.shadow)
    cv.disc(cy - 1, cx - 1, ry, rx, body.base)
    cv.disc(cy - ry // 2, cx - rx // 2, ry * 0.4, rx * 0.42, body.highlight)   # top-left sheen
    cv.rect(h - 2, h - 2, cx - rx + 2, cx + rx - 3, body.shadow)                # ground contact

    # --- face ---
    ey = cy - ry // 3
    n = max(1, int(cfg["eyes"]))
    gap = 4 if n <= 2 else 3
    xs = [cx - gap, cx + gap - 1] if n == 2 else [cx + int((i - (n - 1) / 2) * gap) for i in range(n)]
    for ex in xs:
        cv.rect(ey, ey + 1, ex - 1, ex, (244, 248, 244))     # white
        cv.px(ey + 1, ex - 1, dark); cv.px(ey + 1, ex, dark)  # pupil
    cv.px(ey + 3, cx - 1, dark); cv.px(ey + 3, cx, dark)      # small mouth
    cv.px(cy - ry + 1, cx - rx // 2, (255, 255, 255))         # specular glint

    cv.outline(dark)
    return cv.array()


GHOST_DEFAULT = {"color": (224, 228, 244), "eyes": 2}


def build_ghost(contract, config=None) -> np.ndarray:
    """A floating ghost/wisp — domed top, wavy tail, hollow face. Distinct silhouette
    from the blob; parametric by colour."""
    cfg = {**GHOST_DEFAULT, **(config or {})}
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    cx = w // 2

    cv.disc(13, cx, 7, 8, body.base)                 # domed head
    cv.rect(13, 25, cx - 8, cx + 7, body.base)       # body
    for nx in (cx - 5, cx, cx + 5):                  # wavy tail (scallop notches)
        cv.clear_disc(26, nx, 3.2, 2.4)
    cv.disc(10, cx - 3, 3, 3.2, body.highlight)      # top-left sheen
    cv.rect(13, 24, cx + 6, cx + 7, body.shadow)     # shade side
    cv.rect(24, 25, cx - 3, cx + 2, body.shadow)     # under-shadow

    for ex in (cx - 4, cx + 2):                      # hollow eyes
        cv.rect(13, 15, ex, ex + 1, dark)
    cv.rect(18, 19, cx - 1, cx, dark)                # small mouth
    cv.outline(dark)
    return cv.array()
