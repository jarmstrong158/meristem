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

BLOB_DEFAULT = {"color": (96, 200, 96), "size": "m", "eyes": 2, "build": "slime"}
_SIZE = {"s": (6, 9), "m": (8, 11), "l": (10, 13)}   # (ry, rx)


def _blob_cube(cv, body, cx, cy, ry, rx, h):
    """A gelatinous cube: a rounded translucent block instead of a dome."""
    x0, x1, y0, y1 = cx - rx, cx + rx, cy - ry, cy + ry - 1
    cv.rect(y0, y1, x0, x1, body.base)
    cv.rect(y0, y0 + 2, x0, x0 + 3, body.highlight)  # top-left lit face
    cv.rect(y1 - 2, y1, x1 - 3, x1, body.shadow); cv.rect(y0, y1, x1, x1, body.shadow)   # right/low shade
    for yy, xx in ((y0, x0), (y0, x1), (y1, x0), (y1, x1)):
        cv.clear_disc(yy, xx, 1.3, 1.3)              # round the corners
    cv.px(cy, cx + 1, body.shadow); cv.px(cy + 1, cx + 1, body.shadow)   # a swallowed speck


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
    build = cfg.get("build", "slime")

    if build == "cube":
        _blob_cube(cv, body, cx, cy, ry, rx, h)
    else:
        # --- dome silhouette + directional form shadow (light top-left) ---
        # shadow dome underneath; base dome shifted 1px up-left leaves a thin shadow
        # rim on the bottom-right — clean form shading, not a pillow blob.
        cv.disc(cy, cx, ry, rx, body.shadow)
        cv.disc(cy - 1, cx - 1, ry, rx, body.base)
        cv.disc(cy - ry // 2, cx - rx // 2, ry * 0.4, rx * 0.42, body.highlight)   # top-left sheen
        cv.rect(h - 2, h - 2, cx - rx + 2, cx + rx - 3, body.shadow)                # ground contact
        if build == "ooze":                          # lopsided, dripping
            cv.rect(cy, h - 2, cx - rx, cx - rx + 1, body.shadow)   # left drip down
            cv.disc(h - 3, cx + rx - 2, 2, 1.6, body.base)          # right bulge drip
        if build == "king":                          # crowned slime
            crown = Ramp((240, 210, 90))
            ct = cy - ry - 1
            cv.rect(ct, ct + 1, cx - 3, cx + 2, crown.base)         # band
            for c in (cx - 3, cx - 1, cx + 1, cx + 3):
                cv.px(ct - 1, c, crown.base)                        # points
            cv.px(ct, cx, crown.highlight)

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


GHOST_DEFAULT = {"color": (224, 228, 244), "eyes": 2, "build": "ghost"}


def _ghost_classic(cv, body, dark, cx):
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


def _ghost_wisp(cv, body, dark, cx):
    """A small will-o'-wisp: a glowing orb with a rising flame-tail."""
    cv.disc(20, cx, 5, 5, body.base)                 # round base
    flame = {9: (cx, cx), 10: (cx - 1, cx), 11: (cx - 1, cx + 1),
             12: (cx - 2, cx + 1), 13: (cx - 2, cx + 2), 14: (cx - 3, cx + 2)}
    for r, (c0, c1) in flame.items():
        cv.rect(r, r, c0, c1, body.base)             # tapering flame tongue
    cv.disc(19, cx - 1, 2.2, 2.2, body.highlight)    # bright core
    cv.disc(22, cx + 1, 2, 2.6, body.shadow)
    cv.px(10, cx, (255, 255, 255))                   # tip glint
    cv.px(19, cx - 2, dark); cv.px(19, cx + 2, dark) # tiny eyes


def _ghost_specter(cv, body, dark, cx):
    """A tall hooded phantom with glowing eyes — more menacing than the sheet ghost."""
    cv.disc(9, cx, 5, 6, body.base)                  # hood dome
    cv.rect(9, 27, cx - 6, cx + 5, body.base)        # long robe
    for nx in (cx - 4, cx, cx + 4):                  # ragged hem
        cv.clear_disc(28, nx, 3, 2.2)
    cv.rect(6, 8, cx - 4, cx + 3, body.highlight)    # lit hood crown
    cv.rect(9, 22, cx + 4, cx + 5, body.shadow)      # shade side
    cv.rect(11, 16, cx - 3, cx + 2, body.shadow)     # recessed face (cowl)
    cv.px(12, cx - 2, (240, 96, 96)); cv.px(12, cx + 1, (240, 96, 96))   # glowing eyes


_GHOSTS = {"ghost": _ghost_classic, "wisp": _ghost_wisp, "specter": _ghost_specter}


def build_ghost(contract, config=None) -> np.ndarray:
    """A floating spirit, parametric by colour + `build`: ghost (sheet), wisp
    (will-o'-wisp orb), specter (hooded phantom)."""
    cfg = {**GHOST_DEFAULT, **(config or {})}
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    _GHOSTS.get(cfg.get("build", "ghost"), _ghost_classic)(cv, body, dark, w // 2)
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


FLYER_DEFAULT = {"color": (92, 80, 112), "build": "bat"}

# A front-view winged flyer — fills the bestiary's flying-enemy gap. `build` swaps
# appendages over one skeleton (like the quadruped): membrane vs feather vs round
# wings, ears vs beak. `wing_dy` raises/lowers the wings for the flap animation.
_FLYER_BUILDS = {
    "bat":  {"wing": "membrane", "ears": True,  "beak": False},
    "bird": {"wing": "feather",  "ears": False, "beak": True},
    "moth": {"wing": "round",    "ears": True,  "beak": False},
}


def _flyer_wing(cv, body, kind, wd, side):
    """One wing: an ellipse off the shoulder, lit on top, shaded below. `side` is
    -1 (left) / +1 (right); `wd` is the flap offset (negative = raised)."""
    cx = 16
    ecx = cx + side * 7                              # wing centre column
    ecy = 12 + wd                                    # wing centre row (flap moves it)
    ry, rx = (5, 7) if kind == "round" else (4, 7)
    cv.disc(ecy, ecx, ry, rx, body.base)
    cv.disc(ecy - 1, ecx - side * 2, ry * 0.55, rx * 0.5, body.highlight)   # upper-inner sheen
    cv.disc(ecy + 2, ecx + side, ry * 0.5, rx * 0.55, body.shadow)          # lower shade
    if kind == "membrane":                           # bat: scalloped trailing edge
        for k in (-4, 0, 4):
            cv.clear_disc(ecy + ry - 1, ecx + k, 2.4, 2.0)
    elif kind == "feather":                          # bird: feather-separation lines
        for k in (-3, 1):
            cv.rect(ecy - 2, ecy + 3, ecx + k, ecx + k, body.shadow)


def build_flyer(contract, config=None) -> np.ndarray:
    """A front-view winged beast (bat/bird/moth), parametric by colour + `build`.
    Wings sit behind a furry body; `wing_dy` drives the flap (see flyer_flap)."""
    cfg = {**FLYER_DEFAULT, **(config or {})}
    b = _FLYER_BUILDS.get(cfg["build"], _FLYER_BUILDS["bat"])
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    cx = 16
    wd = int(cfg.get("wing_dy", 0))

    _flyer_wing(cv, body, b["wing"], wd, -1)         # wings first (behind body)
    _flyer_wing(cv, body, b["wing"], wd, +1)

    cv.disc(16, cx, 5, 3, body.base)                 # furry torso
    cv.disc(13, cx - 1, 2, 2.5, body.highlight)      # lit chest (top-left)
    cv.disc(19, cx + 1, 2, 2.5, body.shadow)         # lower-right shade
    cv.disc(9, cx, 3, 3, body.base)                  # head
    cv.disc(8, cx - 1, 1.4, 1.4, body.highlight)

    if b["ears"]:                                    # upright ears
        cv.rect(4, 7, cx - 4, cx - 3, body.base); cv.rect(4, 7, cx + 3, cx + 4, body.base)
        cv.px(4, cx - 4, body.shadow); cv.px(4, cx + 4, body.shadow)
    if b["beak"]:                                    # small down-beak
        cv.px(11, cx, (240, 202, 96)); cv.px(12, cx, (198, 150, 62))

    cv.rect(8, 9, cx - 1, cx - 1, (248, 250, 252)); cv.px(9, cx - 1, dark)   # eyes
    cv.rect(8, 9, cx + 1, cx + 1, (248, 250, 252)); cv.px(9, cx + 1, dark)
    cv.outline(dark)
    return cv.array()


def flyer_flap(contract, config=None) -> list[np.ndarray]:
    """Wing-flap cycle: level -> up -> level -> down. Frame 0 (wing_dy 0) equals the
    static build, so the idle sprite matches."""
    cfg = dict(config or {})
    return [build_flyer(contract, {**cfg, "wing_dy": d}) for d in (0, -3, 0, 3)]


SERPENT_DEFAULT = {"color": (86, 158, 92), "build": "cobra"}

# A reared side-view serpent: a coiled base, an S-rising neck, a raised head. `build`
# swaps the neck/brow: cobra (flared hood), snake (plain), viper (horned brow).
_SERPENT_BUILDS = {
    "cobra": {"hood": True,  "horns": False},
    "snake": {"hood": False, "horns": False},
    "viper": {"hood": False, "horns": True},
}


def build_serpent(contract, config=None) -> np.ndarray:
    """A reared serpent (facing right), parametric by colour + `build`. `tongue`
    flicks the forked tongue and `head_dx` sways the head for the idle."""
    cfg = {**SERPENT_DEFAULT, **(config or {})}
    b = _SERPENT_BUILDS.get(cfg["build"], _SERPENT_BUILDS["cobra"])
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    dx = int(cfg.get("head_dx", 0))

    # --- coiled base (a loop resting on the ground) ---
    cv.disc(24, 14, 5, 9, body.base)                 # coil mass
    cv.clear_disc(24, 13, 2.2, 4.2)                  # the loop's hole
    cv.disc(25, 15, 2.4, 5, body.shadow)             # under-coil shade
    cv.disc(20, 9, 2, 3, body.highlight)             # lit top-left of coil

    # --- rising neck: a gentle S from the coil up to the head (not a straight post) ---
    neck = {20: (15, 18), 19: (15, 18), 18: (14, 17), 17: (13, 16), 16: (13, 16),
            15: (14, 17), 14: (15, 18), 13: (16, 19), 12: (16, 19), 11: (16, 19)}
    for r, (c0, c1) in neck.items():
        cv.rect(r, r, c0, c1, body.base)
        cv.px(r, c0, body.highlight); cv.px(r, c1, body.shadow)      # light left / shade right
    if b["hood"]:                                    # cobra flare
        cv.rect(12, 16, 11, 21, body.base)
        cv.rect(12, 16, 20, 21, body.shadow); cv.rect(12, 16, 11, 12, body.highlight)
        cv.px(14, 13, body.shadow); cv.px(14, 19, body.shadow)       # hood eye-spots

    # --- head (top): a wedge narrowing to a snout up-right, swayed by head_dx ---
    hx = 16 + dx
    cv.rect(8, 11, hx - 2, hx + 2, body.base)        # head mass (wide jaw)
    cv.rect(6, 8, hx, hx + 4, body.base)             # brow -> snout (up-right)
    cv.rect(8, 9, hx - 2, hx - 1, body.highlight)    # lit cheek (top-left)
    cv.rect(10, 11, hx + 1, hx + 2, body.shadow)     # under-jaw shade
    if b["horns"]:                                   # viper brow horns
        cv.px(5, hx + 1, dark); cv.px(5, hx + 3, dark)
    cv.px(8, hx, (240, 214, 78)); cv.px(8, hx + 1, dark)             # eye (yellow + slit)
    # forked tongue flick (from the snout tip, up-right)
    if int(cfg.get("tongue", 0)):
        cv.px(7, hx + 5, (214, 64, 78)); cv.px(7, hx + 6, (214, 64, 78))
        cv.px(6, hx + 7, (214, 64, 78)); cv.px(8, hx + 7, (214, 64, 78))

    cv.outline(dark)
    return cv.array()


def serpent_idle(contract, config=None) -> list[np.ndarray]:
    """Idle: tongue flick + a 1px head sway. Frame 0 (no tongue, centred) is static."""
    cfg = dict(config or {})
    states = [(0, 0), (1, 0), (0, 1), (1, 0)]        # (tongue, head_dx)
    return [build_serpent(contract, {**cfg, "tongue": t, "head_dx": d}) for t, d in states]


SPIDER_DEFAULT = {"color": (74, 66, 82), "build": "spider"}

# A front-view spider: abdomen + cephalothorax + 8 radiating bent legs. `build`
# swaps markings/leg weight: spider (plain), tarantula (thick legs), widow (red mark).
_SPIDER_BUILDS = {
    "spider":    {"thick": False, "mark": None},
    "tarantula": {"thick": True,  "mark": None},
    "widow":     {"thick": False, "mark": (206, 54, 60)},
}
# leg anchors on the cephalothorax and their knee/foot targets (left side; right mirrors)
_SPIDER_LEGS = [((10, 12), (6, 4), (8, 2)), ((11, 12), (9, 4), (13, 2)),
                ((13, 12), (13, 4), (17, 3)), ((14, 12), (16, 5), (20, 5))]


def build_spider(contract, config=None) -> np.ndarray:
    """A front-view spider, parametric by colour + `build`. `leg_dy` twitches the
    legs for the skitter idle."""
    cfg = {**SPIDER_DEFAULT, **(config or {})}
    b = _SPIDER_BUILDS.get(cfg["build"], _SPIDER_BUILDS["spider"])
    body = Ramp(cfg["color"])
    dark = outline_dark(cfg["color"])
    w, h = contract.canvas_of("enemy")
    cv = Canvas(w, h)
    cx = 16
    jig = int(cfg.get("leg_dy", 0))

    # --- 8 bent legs (behind the body); alternate sides twitch on opposite frames ---
    for i, ((ar, ac), (kr, kc), (fr, fc)) in enumerate(_SPIDER_LEGS):
        for side in (-1, 1):
            dy = jig if (i % 2 == 0) == (side < 0) else -jig      # opposite legs alternate
            a = (ar, cx + side * (ac - cx))
            k = (kr + dy, cx + side * (kc - cx))
            f = (fr + dy, cx + side * (fc - cx))
            cv.line(a[0], a[1], k[0], k[1], body.base)           # thigh
            cv.line(k[0], k[1], f[0], f[1], body.shadow)         # shin (shaded)
            if b["thick"]:                                       # tarantula: doubled
                cv.line(a[0] + 1, a[1], k[0], k[1], body.base)

    # --- body: abdomen (big, low) + cephalothorax (small, high) ---
    cv.disc(19, cx, 5, 6, body.base)
    cv.disc(21, cx + 1, 3, 4, body.shadow)           # lower-right shade
    cv.disc(16, cx - 1, 2, 2.5, body.highlight)      # top-left sheen
    if b["mark"]:                                    # widow hourglass
        cv.px(19, cx, b["mark"]); cv.px(20, cx, b["mark"])
        cv.px(18, cx, b["mark"]); cv.px(21, cx, b["mark"])
    cv.disc(11, cx, 3, 4, body.base)                 # cephalothorax
    cv.disc(10, cx - 1, 1.4, 1.6, body.highlight)

    for ex in (cx - 2, cx, cx + 2):                  # cluster of eyes
        cv.px(10, ex, dark)
    cv.px(9, cx - 1, (240, 240, 250)); cv.px(9, cx + 1, (240, 240, 250))
    cv.px(14, cx - 1, dark); cv.px(14, cx + 1, dark)  # chelicerae/fangs

    cv.outline(dark)
    return cv.array()


def spider_idle(contract, config=None) -> list[np.ndarray]:
    """Skitter: legs twitch, alternating sides. Frame 0 (leg_dy 0) is static."""
    cfg = dict(config or {})
    return [build_spider(contract, {**cfg, "leg_dy": d}) for d in (0, 1, 0, 1)]
