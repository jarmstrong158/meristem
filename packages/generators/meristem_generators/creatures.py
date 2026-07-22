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


QUADRUPED_DEFAULT = {"color": (150, 118, 86)}


def build_quadruped(contract, config=None) -> np.ndarray:
    """A side-view four-legged beast (facing right), built to the quadruped spec
    (docs/research/03-quadruped.md): three masses on a curved spine; TWO sets of biped
    legs — the far pair darker + offset + paws 1px higher (depth), front legs vertical,
    back legs Z-bent; tucked belly, raised withers. Parametric colour."""
    cfg = {**QUADRUPED_DEFAULT, **(config or {})}
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)

    # --- FAR leg pair (behind): shadow, thin, paws 1px high (row 27). Distinct columns. ---
    cv.rect(15, 19, 7, 8, body.shadow); cv.rect(19, 27, 6, 7, body.shadow)   # far-back (Z)
    cv.rect(27, 27, 5, 7, body.shadow)
    cv.rect(15, 27, 16, 17, body.shadow); cv.rect(27, 27, 16, 18, body.shadow)  # far-front

    # --- BODY loaf: curved back (withers high), belly at row 15, tucked toward rear ---
    body_rows = {10: (19, 23), 11: (9, 25), 12: (7, 27), 13: (7, 28),
                 14: (8, 27), 15: (10, 24)}
    for r, (c0, c1) in body_rows.items():
        cv.rect(r, r, c0, c1, body.base)
    cv.rect(11, 12, 10, 23, body.highlight)          # spine highlight (top of back)
    cv.rect(14, 15, 9, 25, body.shadow)              # belly underside (darkest)

    # --- NEAR leg pair (front): base, distinct columns, paws on ground (row 28) ---
    cv.rect(15, 19, 11, 12, body.base); cv.rect(19, 28, 10, 11, body.base)   # near-back (Z-bend)
    cv.rect(28, 28, 9, 11, body.base)
    cv.rect(15, 28, 20, 21, body.base); cv.rect(28, 28, 20, 22, body.base)   # near-front (vertical)
    cv.rect(15, 27, 20, 20, body.highlight)          # lit front edge

    # --- HEAD + neck + muzzle (front-right) ---
    cv.rect(11, 15, 20, 24, body.base)               # diagonal neck
    cv.rect(8, 14, 23, 29, body.base)                # skull
    cv.rect(12, 14, 28, 31, body.base)               # muzzle wedge (forward)
    cv.rect(8, 9, 24, 28, body.highlight)            # skull top highlight
    cv.rect(14, 14, 24, 31, body.shadow)             # muzzle/jaw underside
    cv.px(13, 31, dark)                              # nose
    cv.px(11, 28, dark)                              # eye (single pixel, high-front)
    cv.rect(6, 8, 23, 24, body.base); cv.rect(6, 8, 26, 27, body.base)   # upright ears (top-back)
    cv.px(8, 24, body.shadow); cv.px(8, 27, body.shadow)

    # --- TAIL: from rump, sweeps down-left with a curl ---
    cv.rect(12, 16, 4, 7, body.base); cv.rect(11, 13, 2, 5, body.base)
    cv.rect(15, 16, 4, 6, body.shadow)               # underside

    cv.outline(dark)
    return cv.array()
