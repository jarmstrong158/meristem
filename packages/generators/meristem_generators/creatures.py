"""Creature archetypes (dec-0022): parametric recipes, not per-name builders.

`blob` is the first — a slime/ooze/jelly is `blob(color=..., size=..., eyes=...)`,
not hand-drawn each time. Built to the sprite standard (dec-0021): one material ramp
(shadow cool / base / highlight warm), directional top-left light, selective outline,
a readable rounded silhouette. This is the "easier/better way to make slimes".
"""
from __future__ import annotations

import numpy as np

from .shading import Ramp
from .sprite import Canvas, outline_dark, translate

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
    sq = int(cfg.get("squash", 0))                    # squash-and-stretch (idle anim)
    ry = max(3, ry - sq); rx = rx + sq                # squash: shorter + wider
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


def blob_idle(contract, config=None) -> list[np.ndarray]:
    """Squash-and-stretch idle: rest -> squash down -> rest -> stretch up. Frame 0
    equals the static build (squash 0), so the compiler's idle sprite matches it."""
    cfg = dict(config or {})
    return [build_blob(contract, {**cfg, "squash": s}) for s in (0, 1, 0, -1)]


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


def ghost_idle(contract, config=None) -> list[np.ndarray]:
    """Float bob: the whole ghost drifts up 2px and back (rigid translate, so no new
    colours). Frame 0 is the un-shifted static build."""
    base = build_ghost(contract, config)
    return [translate(base, dy=d) for d in (0, -1, -2, -1)]


QUADRUPED_DEFAULT = {"color": (150, 118, 86), "build": "dog"}

# Proportion/appendage knobs over the fixed quadruped skeleton (research 03 §6).
# paw   = ground row for the near legs (leg length; far paws sit 1px higher)
# ear   = ear height in px (upright pointed vs small)
# muzzle= how far the snout juts right (short face vs long snout)
# tail  = tail style: "curl" up, "low" straight-down, "stub" tiny, "scurve" long S
_QUAD_BUILDS = {
    "dog":  {"paw": 28, "ear": 2, "muzzle": 30, "tail": "curl"},    # balanced
    "wolf": {"paw": 29, "ear": 3, "muzzle": 31, "tail": "low"},     # leggy, tall ears, long
    "boar": {"paw": 27, "ear": 1, "muzzle": 31, "tail": "stub"},    # low & heavy, long snout
    "cat":  {"paw": 28, "ear": 1, "muzzle": 29, "tail": "scurve"},  # slim, short face
}


def _quad_tail(cv, body, style):
    """Draw a build-specific tail off the rump (left edge, ~col 2-7)."""
    if style == "curl":                              # dog: sweeps down then curls up
        cv.rect(12, 16, 4, 7, body.base); cv.rect(11, 13, 2, 5, body.base)
        cv.rect(15, 16, 4, 6, body.shadow)
    elif style == "low":                             # wolf: long, hangs low & straight
        cv.rect(13, 22, 4, 6, body.base)
        cv.rect(18, 22, 4, 5, body.shadow)
    elif style == "stub":                            # boar: tiny nub
        cv.rect(13, 15, 5, 7, body.base)
        cv.rect(15, 15, 5, 6, body.shadow)
    elif style == "scurve":                          # cat: long, tall S-curve
        cv.rect(9, 15, 5, 7, body.base); cv.rect(8, 10, 6, 9, body.base)
        cv.rect(12, 15, 5, 5, body.shadow)


def build_quadruped(contract, config=None) -> np.ndarray:
    """A side-view four-legged beast (facing right), built to the quadruped spec
    (docs/research/03-quadruped.md): a thick body loaf on a curved spine; TWO sets of
    biped legs — the far pair darker + paws 1px higher (depth), the near pair on the
    ground; legs hang *below* the body with 3px gaps so they read as four and never
    fuse into a floor. Parametric by colour and `build` (dog/wolf/boar/cat) — the
    build knobs (leg length, ears, muzzle, tail) reshape the one skeleton (§6)."""
    cfg = {**QUADRUPED_DEFAULT, **(config or {})}
    b = _QUAD_BUILDS.get(cfg["build"], _QUAD_BUILDS["dog"])
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    npaw, fpaw = b["paw"], b["paw"] - 1              # near on ground, far 1px higher

    # --- FAR leg pair (behind): shadow, thin 2px, tuck under belly (row 17).
    # Legs at cols 6/11/16/21 -> 3px gaps that survive the outline (a 2px gap gets
    # closed when both sides are outlined, fusing the paws into a floor). ---
    cv.rect(17, fpaw, 6, 7, body.shadow)             # far-back
    cv.rect(17, fpaw, 16, 17, body.shadow)           # far-front

    # --- BODY loaf: THICK. ~9 rows tall (9-17), wide (cols 6-28) with a WIDE belly
    # so the legs hang below it and the body reads as a full beast, not a rail. The
    # legs start at row 18 (below the body) so they never eat into its thickness.
    body_rows = {9: (19, 24), 10: (11, 26), 11: (8, 27), 12: (6, 28), 13: (6, 28),
                 14: (6, 28), 15: (6, 28), 16: (6, 27), 17: (6, 25)}
    for r, (c0, c1) in body_rows.items():
        cv.rect(r, r, c0, c1, body.base)
    cv.rect(11, 13, 10, 22, body.highlight)          # broad spine highlight (top of back)
    cv.rect(16, 17, 8, 25, body.shadow)              # belly underside (darkest)

    # --- NEAR leg pair (front): base, thin 2px, on the ground ---
    cv.rect(18, npaw, 11, 12, body.base)             # near-back
    cv.rect(18, npaw, 21, 22, body.base)             # near-front
    cv.rect(18, npaw - 1, 21, 21, body.highlight)    # lit front edge

    # --- HEAD + neck + muzzle (front-right); muzzle length is a build knob.
    # `head_dy` bobs the head (not the neck root) for a breathing idle. ---
    mz = b["muzzle"]
    hd = int(cfg.get("head_dy", 0))
    cv.rect(11, 15, 20, 24, body.base)               # diagonal neck (fixed to body)
    cv.rect(8 + hd, 14 + hd, 23, 29, body.base)      # skull
    cv.rect(12 + hd, 14 + hd, 28, mz, body.base)     # muzzle wedge (juts to `mz`)
    cv.rect(8 + hd, 9 + hd, 24, 28, body.highlight)  # skull top highlight
    cv.rect(14 + hd, 14 + hd, 24, mz, body.shadow)   # muzzle/jaw underside
    cv.px(13 + hd, mz, dark)                         # nose (tip of snout)
    cv.px(11 + hd, 28, dark)                         # eye (single pixel, high-front)
    ear_top = 8 - b["ear"]                            # taller ears reach higher
    cv.rect(ear_top + hd, 8 + hd, 23, 24, body.base); cv.rect(ear_top + hd, 8 + hd, 26, 27, body.base)
    cv.px(8 + hd, 24, body.shadow); cv.px(8 + hd, 27, body.shadow)

    # --- TAIL: build-specific silhouette off the rump ---
    _quad_tail(cv, body, b["tail"])

    cv.outline(dark)
    return cv.array()


def quadruped_idle(contract, config=None) -> list[np.ndarray]:
    """Gentle breathing idle: the head dips 1px and lifts. Frame 0 is the static
    build (head_dy 0)."""
    cfg = dict(config or {})
    return [build_quadruped(contract, {**cfg, "head_dy": d}) for d in (0, 0, 1, 0)]
