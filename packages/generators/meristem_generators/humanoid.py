"""LPC-style layered humanoid (dec-0022).

A humanoid is a stack of z-ordered LAYERS (base body -> pants -> shirt -> hair ->
face -> [future: gear/weapon]) all registered to ONE shared skeleton. The skeleton
is a `Pose` (per-region vertical offsets) that changes per animation frame; every
layer reads the same pose, so animation is inherited by every layer and any new
part (a hat, armor, a sword) animates for free. Materials come from `config`, so a
per-character palette is just a different config — no new code.

This is the scalable replacement for the one-off `build_hero`: bodies, hair, and
clothes are slots, and the walk cycle is the shared frame template — the LPC pattern
at 32x32.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .shading import Ramp, shadow as _sh
from .sprite import Canvas


@dataclass
class Pose:
    """Skeleton state for one frame: vertical offsets per region (front view)."""
    body_dy: int = 0        # head + neck + torso (and hair/face, which ride the head)
    larm_dy: int = 0        # left arm swing (added to body_dy)
    rarm_dy: int = 0        # right arm swing
    lleg_dy: int = 0        # left leg / foot lift
    rleg_dy: int = 0        # right leg / foot lift


IDLE = Pose()
# Walk: step frames dip the body 1px onto the planted foot while the OTHER foot
# lifts; arms swing in opposition. Stand frames are the tall neutral (= idle).
_STEP_A = Pose(body_dy=1, rleg_dy=-1, larm_dy=1, rarm_dy=-1)   # right foot lifts, left arm fwd
_STEP_B = Pose(body_dy=1, lleg_dy=-1, rarm_dy=1, larm_dy=-1)   # left foot lifts, right arm fwd
WALK = [_STEP_A, IDLE, _STEP_B, IDLE]

DEFAULT_CONFIG = {
    "skin": (232, 176, 136),
    "hair": (112, 68, 40),
    "shirt": (56, 126, 196),
    "pants": (78, 72, 98),
    "hair_style": "short",
    "beard": "none",
    "hat": "none",
    "hat_color": (150, 62, 68),
}


def _r(cv: Canvas, r0, r1, c0, c1, rgb, dy=0):
    cv.rect(r0 + dy, r1 + dy, c0, c1, rgb)


def _p(cv: Canvas, r, c, rgb, dy=0):
    cv.px(r + dy, c, rgb)


# ---- layers (drawn low z -> high z); each reads the shared pose ----
def _base_body(cv, pose, skin):
    u = pose.body_dy
    _r(cv, 7, 13, 12, 19, skin.base, u)                      # face
    _r(cv, 14, 14, 14, 17, skin.base, u)                     # neck
    _r(cv, 15, 22, 12, 19, skin.base, u)                     # torso (under shirt)
    _r(cv, 15, 21, 10, 10, skin.base, u + pose.larm_dy)      # left arm (under sleeve)
    _r(cv, 15, 21, 21, 21, skin.base, u + pose.rarm_dy)      # right arm
    _r(cv, 20, 21, 10, 10, skin.base, u + pose.larm_dy)      # left hand
    _r(cv, 20, 21, 21, 21, skin.shadow, u + pose.rarm_dy)    # right hand (shade side)
    _r(cv, 23, 29, 12, 14, skin.base, pose.lleg_dy)          # legs (under pants)
    _r(cv, 23, 29, 17, 19, skin.base, pose.rleg_dy)


def _pants(cv, pose, pants, dark):
    for cols, dy in (((12, 14), pose.lleg_dy), ((17, 19), pose.rleg_dy)):
        c0, c1 = cols
        _r(cv, 23, 28, c0, c1, pants.base, dy)
        _r(cv, 23, 28, c1 if c0 == 12 else c0, c1 if c0 == 12 else c0, pants.shadow, dy)  # inner/outer shade
        _r(cv, 29, 29, c0, c1, pants.shadow, dy)             # boot
        _p(cv, 29, c1 if c0 == 12 else c0, dark, dy)         # sole
    _p(cv, 23, 12, pants.highlight, pose.lleg_dy)


def _shirt(cv, pose, shirt):
    u = pose.body_dy
    _r(cv, 15, 21, 12, 19, shirt.base, u)                    # torso
    _r(cv, 16, 17, 11, 20, shirt.base, u)                    # shoulders
    _r(cv, 15, 16, 12, 14, shirt.highlight, u)               # lit shoulder (top-left)
    _r(cv, 15, 21, 19, 19, shirt.shadow, u)                  # shade side
    _r(cv, 21, 21, 12, 19, shirt.shadow, u)                  # waist
    _r(cv, 15, 19, 10, 10, shirt.base, u + pose.larm_dy)     # left sleeve (hand shows below)
    _r(cv, 15, 19, 21, 21, shirt.shadow, u + pose.rarm_dy)   # right sleeve


# ---- hair styles: a config knob over the shared head; each reads the pose so it
#      animates for free. `bald` draws nothing. ----
def _hair_short(cv, u, hair):
    _r(cv, 2, 2, 13, 18, hair.base, u); _r(cv, 3, 3, 12, 19, hair.base, u)
    _r(cv, 4, 5, 11, 20, hair.base, u); _r(cv, 6, 6, 12, 19, hair.base, u)
    _r(cv, 7, 9, 11, 11, hair.base, u); _r(cv, 7, 9, 20, 20, hair.base, u)   # sideburns
    _r(cv, 2, 3, 13, 15, hair.highlight, u)                                   # warm highlight
    _p(cv, 4, 12, hair.highlight, u); _p(cv, 4, 13, hair.highlight, u)
    _r(cv, 3, 6, 19, 20, hair.shadow, u)                                      # cool shade side
    _p(cv, 7, 20, hair.shadow, u); _p(cv, 8, 20, hair.shadow, u); _p(cv, 9, 20, hair.shadow, u)
    _r(cv, 6, 6, 13, 18, hair.shadow, u)                                      # hairline cast shadow


def _hair_long(cv, u, hair):
    _hair_short(cv, u, hair)                                                   # same cap on top
    _r(cv, 7, 18, 10, 11, hair.base, u); _r(cv, 7, 18, 20, 21, hair.base, u)  # falls past shoulders
    _r(cv, 8, 18, 10, 10, hair.highlight, u)                                   # lit left fall
    _r(cv, 8, 18, 21, 21, hair.shadow, u)                                      # shaded right fall
    _r(cv, 18, 18, 10, 11, hair.shadow, u); _r(cv, 18, 18, 20, 21, hair.shadow, u)   # tips


def _hair_ponytail(cv, u, hair):
    _hair_short(cv, u, hair)
    _r(cv, 5, 6, 20, 22, hair.base, u); _r(cv, 7, 14, 21, 22, hair.base, u)   # tail down the right
    _r(cv, 7, 14, 22, 22, hair.shadow, u); _p(cv, 6, 21, hair.highlight, u)


def _hair_spiky(cv, u, hair):
    for c in (11, 13, 15, 17, 19):
        _r(cv, 1, 3, c, c, hair.base, u)                                      # upright spikes
    _r(cv, 4, 5, 11, 20, hair.base, u); _r(cv, 6, 6, 12, 19, hair.base, u)    # base mass
    _r(cv, 7, 9, 11, 11, hair.base, u); _r(cv, 7, 9, 20, 20, hair.base, u)    # sideburns
    _p(cv, 2, 13, hair.highlight, u); _p(cv, 2, 15, hair.highlight, u)
    _r(cv, 4, 6, 19, 20, hair.shadow, u); _r(cv, 6, 6, 13, 18, hair.shadow, u)


_HAIR = {"short": _hair_short, "long": _hair_long, "ponytail": _hair_ponytail,
         "spiky": _hair_spiky, "bald": lambda cv, u, hair: None}


def _hair(cv, pose, hair, style):
    _HAIR.get(style, _hair_short)(cv, pose.body_dy, hair)


# ---- beard layer (drawn over the face; `full` covers the mouth) ----
def _beard_short(cv, u, hair):
    _r(cv, 12, 13, 12, 19, hair.base, u)                                      # jaw stubble
    _r(cv, 13, 13, 13, 18, hair.shadow, u)


def _beard_full(cv, u, hair):
    _r(cv, 11, 15, 12, 19, hair.base, u); _r(cv, 16, 16, 13, 18, hair.base, u)   # full beard
    _r(cv, 11, 12, 12, 14, hair.highlight, u)                                 # lit left
    _r(cv, 12, 16, 19, 19, hair.shadow, u)                                    # shade right
    _r(cv, 8, 10, 11, 11, hair.base, u); _r(cv, 8, 10, 20, 20, hair.base, u)  # connects to sideburns


_BEARDS = {"none": lambda cv, u, hair: None, "short": _beard_short, "full": _beard_full}


def _beard(cv, pose, hair, style):
    _BEARDS.get(style, _BEARDS["none"])(cv, pose.body_dy, hair)


# ---- hat layer (drawn last, over hair; helmet/cap cover the crown) ----
def _hat_cap(cv, u, hat):
    _r(cv, 4, 6, 11, 20, hat.base, u); _r(cv, 3, 3, 12, 19, hat.base, u)
    _r(cv, 6, 6, 10, 21, hat.base, u)                                         # brim
    _r(cv, 3, 4, 12, 15, hat.highlight, u); _r(cv, 4, 6, 19, 20, hat.shadow, u)


def _hat_wizard(cv, u, hat):
    cone = {0: (15, 16), 1: (15, 16), 2: (14, 17), 3: (14, 17), 4: (13, 18), 5: (13, 18)}
    for r, (c0, c1) in cone.items():
        _r(cv, r, r, c0, c1, hat.base, u)
    _r(cv, 6, 6, 10, 21, hat.base, u); _r(cv, 6, 6, 10, 21, hat.shadow, u)    # wide brim
    _r(cv, 0, 4, 15, 15, hat.highlight, u); _r(cv, 2, 5, 18, 18, hat.shadow, u)
    _p(cv, 4, 16, hat.highlight, u)                                           # band glint (reuse ramp)


def _hat_helmet(cv, u, hat):
    _r(cv, 3, 7, 11, 20, hat.base, u); _r(cv, 2, 2, 13, 18, hat.base, u)      # dome
    _r(cv, 3, 4, 12, 14, hat.highlight, u); _r(cv, 3, 7, 19, 20, hat.shadow, u)
    _r(cv, 7, 9, 11, 11, hat.base, u); _r(cv, 7, 9, 20, 20, hat.base, u)      # cheek guards
    _r(cv, 7, 11, 15, 16, hat.base, u); _r(cv, 7, 11, 16, 16, hat.shadow, u)  # nasal guard


def _hat_crown(cv, u, hat):
    _r(cv, 4, 6, 11, 20, hat.base, u)                                         # band
    for c in (11, 13, 15, 17, 19):
        _r(cv, 2, 3, c, c, hat.base, u)                                       # points
    _r(cv, 4, 4, 12, 15, hat.highlight, u); _r(cv, 6, 6, 11, 20, hat.shadow, u)
    _p(cv, 3, 15, hat.highlight, u)                                           # centre jewel-glint (reuse ramp)


_HATS = {"none": lambda cv, u, hat: None, "cap": _hat_cap, "wizard": _hat_wizard,
         "helmet": _hat_helmet, "crown": _hat_crown}


def _hat(cv, pose, hat, style):
    _HATS.get(style, _HATS["none"])(cv, pose.body_dy, hat)


def _face(cv, pose, eye, skin):
    u = pose.body_dy
    _r(cv, 9, 10, 13, 13, eye, u); _r(cv, 9, 10, 18, 18, eye, u)              # eyes
    _p(cv, 12, 15, skin.shadow, u); _p(cv, 12, 16, skin.shadow, u)            # mouth


def build_frame(contract, config, pose) -> np.ndarray:
    w, h = contract.canvas_of("character")
    mats = {**DEFAULT_CONFIG, **(config or {})}
    skin, hair = Ramp(mats["skin"]), Ramp(mats["hair"])
    shirt, pants = Ramp(mats["shirt"]), Ramp(mats["pants"])
    dark = _sh(mats["hair"], 0.68)                            # shared eye + outline + sole
    cv = Canvas(w, h)
    _base_body(cv, pose, skin)
    _pants(cv, pose, pants, dark)
    _shirt(cv, pose, shirt)
    _hair(cv, pose, hair, mats.get("hair_style", "short"))
    _face(cv, pose, dark, skin)
    _beard(cv, pose, hair, mats.get("beard", "none"))        # over the face
    _hat(cv, pose, Ramp(mats["hat_color"]), mats.get("hat", "none"))   # over the crown
    cv.outline(dark)
    return cv.array()


def build_humanoid(contract, config=None) -> np.ndarray:
    return build_frame(contract, config, IDLE)


def humanoid_walk(contract, config=None) -> list[np.ndarray]:
    return [build_frame(contract, config, p) for p in WALK]
