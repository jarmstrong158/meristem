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
    # ---- prop / accessory layers (dec: distinctness is silhouette, not palette) ----
    # Each is a config knob over the shared Pose, so it animates for free and is
    # outlined by the one shared pass. Defaults are inert (none/boots/normal), so
    # every pre-existing character renders identically.
    "held": "none",              # every weapon kind + rod/flamestaff/shield/daggers (see _HELD)
    "held_color": (150, 120, 84),
    "garment": "none",           # apron · scarf · cloak (over the shirt)
    "garment_color": (204, 192, 162),
    "feet": "boots",             # boots · bare
    "arms": "normal",            # normal · stone (reinforced forearms)
    "arm_color": (132, 136, 142),
    "hair_accent": "none",       # flora (sprigs tucked in the hair)
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


def _hat_hood(cv, u, hat):
    _r(cv, 2, 6, 10, 21, hat.base, u)                                        # crown mass
    _r(cv, 6, 13, 10, 11, hat.base, u); _r(cv, 6, 13, 20, 21, hat.base, u)   # side falls framing face
    _r(cv, 6, 13, 10, 10, hat.shadow, u); _r(cv, 6, 13, 21, 21, hat.shadow, u)
    _r(cv, 2, 3, 11, 14, hat.highlight, u)                                   # lit crown (top-left)
    _r(cv, 6, 6, 12, 19, hat.shadow, u)                                      # inner brim cast over brow


_HATS = {"none": lambda cv, u, hat: None, "cap": _hat_cap, "wizard": _hat_wizard,
         "helmet": _hat_helmet, "crown": _hat_crown, "hood": _hat_hood}


def _hat(cv, pose, hat, style):
    _HATS.get(style, _HATS["none"])(cv, pose.body_dy, hat)


def _face(cv, pose, eye, skin):
    u = pose.body_dy
    _r(cv, 9, 10, 13, 13, eye, u); _r(cv, 9, 10, 18, 18, eye, u)              # eyes
    _p(cv, 12, 15, skin.shadow, u); _p(cv, 12, 16, skin.shadow, u)            # mouth


# ---- held items: ride a hand/leg offset so they swing with the walk; drawn
#      front-most, then caught by the one shared outline pass (no self-outline). ----
def _held_shaft(cv, pose, m, *, side, ember=None, notched=False):
    c = 8 if side == "left" else 22
    dy = pose.larm_dy if side == "left" else pose.rarm_dy
    _r(cv, 2, 30, c, c, m.base, dy)                                          # shaft
    _p(cv, 3, c, m.highlight, dy); _p(cv, 4, c, m.highlight, dy)             # lit upper
    _r(cv, 27, 30, c, c, m.shadow, dy)                                       # shaded foot
    if notched:                                                             # Lida's tally rod
        for nr in (12, 16, 20, 24):
            _p(cv, nr, c, m.shadow, dy)
    if ember is not None:                                                    # smoldering flame tip
        _r(cv, 2, 3, c - 1, c + 1, ember.base, dy)                          # flame body
        _p(cv, 1, c, ember.base, dy); _p(cv, 1, c - 1, ember.shadow, dy)
        _p(cv, 0, c, ember.highlight, dy)                                   # licking tip
        _p(cv, 3, c, (255, 240, 180), dy)                                   # hot core


def _held_shield(cv, pose, m):
    dy = pose.body_dy + pose.larm_dy
    cy, cx = 18.0 + dy, 8.5
    cv.disc(cy, cx, 5.0, 4.2, m.base)                                        # face
    cv.disc(cy - 1.4, cx - 1.4, 2.0, 1.7, m.highlight)                       # top-left sheen
    cv.px(int(cy), 8, m.shadow); cv.px(int(cy) + 1, 9, m.shadow)             # boss
    cv.disc(cy, cx, 1.3, 1.1, m.base)


def _held_daggers(cv, pose, m):
    steel = Ramp((178, 186, 200))                                          # bright blade, reads at 1x
    for c, dy in ((9, pose.larm_dy), (22, pose.rarm_dy)):                    # held point-down beside each hand
        u = pose.body_dy + dy
        _r(cv, 20, 21, c, c, m.base, u)                                     # grip in the fist
        _r(cv, 22, 22, c - 1, c + 1, m.shadow, u)                           # crossguard
        _r(cv, 23, 27, c, c, steel.base, u)                                 # blade
        _p(cv, 23, c, steel.highlight, u)                                   # lit edge
        _p(cv, 28, c, steel.shadow, u)                                      # point


# ---- every weapon kind, held upright in the right hand (col 22). Steel blade +
#      gold fittings are fixed; `held_color` tints the haft/grip. ----
_H_STEEL = (178, 186, 200)
_H_GOLD = (214, 176, 72)
_H_GEM = (120, 200, 235)


def _held_sword(cv, pose, m, *, big=False):
    dy = pose.body_dy + pose.rarm_dy
    st, gd = Ramp(_H_STEEL), Ramp(_H_GOLD)
    if big:                                                  # greatsword: long 2px blade, two-hand grip
        _r(cv, 4, 16, 21, 22, st.base, dy)
        _r(cv, 4, 16, 21, 21, st.highlight, dy); _r(cv, 4, 16, 22, 22, st.shadow, dy)
        _p(cv, 3, 21, st.highlight, dy)
        _r(cv, 17, 17, 20, 23, gd.base, dy)                 # wide guard
        _r(cv, 18, 21, 21, 22, m.base, dy)                  # grip
    else:
        _r(cv, 9, 17, 22, 22, st.base, dy); _p(cv, 8, 22, st.highlight, dy)   # blade + tip
        _p(cv, 9, 22, st.highlight, dy)
        _r(cv, 18, 18, 21, 23, gd.base, dy)                 # crossguard
        _r(cv, 19, 21, 22, 22, m.base, dy)                  # grip


def _held_knife(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    st, gd = Ramp(_H_STEEL), Ramp(_H_GOLD)
    _r(cv, 14, 18, 22, 22, st.base, dy); _p(cv, 13, 22, st.highlight, dy)     # short blade
    _r(cv, 19, 19, 21, 23, gd.base, dy)                     # guard
    _r(cv, 20, 21, 22, 22, m.base, dy)                      # grip


def _held_axe(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    st = Ramp(_H_STEEL)
    _r(cv, 6, 21, 22, 22, m.base, dy); _p(cv, 7, 22, m.highlight, dy)         # haft
    for r, (c0, c1) in {6: (19, 21), 7: (19, 22), 8: (19, 22), 9: (20, 21)}.items():
        _r(cv, r, r, c0, c1, st.base, dy)                   # blade head (upper-left)
    _p(cv, 6, 19, st.highlight, dy); _p(cv, 8, 19, st.shadow, dy)


def _held_spear(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    st = Ramp(_H_STEEL)
    _r(cv, 4, 21, 22, 22, m.base, dy); _p(cv, 5, 22, m.highlight, dy)         # long shaft
    for r, (c0, c1) in {0: (22, 22), 1: (21, 23), 2: (21, 23), 3: (22, 22)}.items():
        _r(cv, r, r, c0, c1, st.base, dy)                   # leaf tip (centred on the shaft)
    _p(cv, 1, 21, st.highlight, dy); _p(cv, 2, 23, st.shadow, dy)


def _held_mace(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    st = Ramp(_H_STEEL)
    _r(cv, 11, 21, 23, 23, m.base, dy)                      # handle
    for r, c in [(3, 23), (4, 20), (5, 26), (9, 21), (9, 25), (4, 26)]:
        cv.line(7 + dy, 23, r + dy, c, st.shadow)           # spikes from the ball centre
    cv.disc(7 + dy, 23, 2.6, 2.6, st.base)                  # ball over the spike roots
    cv.disc(6 + dy, 22, 1.0, 1.0, st.highlight)


def _held_bow(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    for r, c in {6: 22, 7: 23, 8: 24, 9: 24, 10: 24, 11: 24, 12: 24, 13: 23, 14: 22}.items():
        _p(cv, r, c, m.base, dy)                            # vertical bow limb (curves right)
    _r(cv, 7, 13, 22, 22, Ramp(_H_STEEL).highlight, dy)     # string down the near side


def _held_wand(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    o = Ramp(_H_GEM)
    _r(cv, 14, 21, 22, 22, m.base, dy)                      # short rod
    cv.disc(12 + dy, 22, 1.8, 1.8, o.base); cv.px(11 + dy, 21, (255, 255, 255))   # gem tip


_HELD_FNS = {
    "staff":      lambda cv, p, m: _held_shaft(cv, p, m, side="left"),
    "rod":        lambda cv, p, m: _held_shaft(cv, p, m, side="right", notched=True),
    "flamestaff": lambda cv, p, m: _held_shaft(cv, p, m, side="left", ember=Ramp((224, 100, 52))),
    "shield":     _held_shield,
    "daggers":    _held_daggers,
    "sword":      _held_sword,
    "greatsword": lambda cv, p, m: _held_sword(cv, p, m, big=True),
    "dagger":     _held_knife,
    "axe":        _held_axe,
    "spear":      _held_spear,
    "mace":       _held_mace,
    "bow":        _held_bow,
    "wand":       _held_wand,
}


def _held(cv, pose, mats):
    fn = _HELD_FNS.get(mats.get("held", "none"))
    if fn is not None:
        fn(cv, pose, Ramp(mats["held_color"]))


# ---- garment: over-clothing drawn on top of the shirt (before hair) ----
def _garment_apron(cv, pose, m):
    u = pose.body_dy
    _r(cv, 17, 22, 13, 18, m.base, u)                                        # bib over torso
    _r(cv, 17, 17, 13, 14, m.highlight, u); _r(cv, 17, 22, 18, 18, m.shadow, u)
    _r(cv, 20, 20, 14, 17, m.shadow, u)                                      # bib pocket seam
    _r(cv, 23, 27, 13, 18, m.base); _r(cv, 23, 27, 18, 18, m.shadow)         # skirt over the lap
    _r(cv, 25, 25, 14, 17, m.shadow)                                         # skirt pocket seam


def _garment_scarf(cv, pose, m):
    u = pose.body_dy
    _r(cv, 14, 14, 12, 19, m.base, u); _r(cv, 14, 14, 12, 13, m.highlight, u)   # around the neck
    _r(cv, 15, 20, 12, 12, m.base, u); _r(cv, 15, 20, 13, 13, m.shadow, u)      # tail down the front
    _p(cv, 21, 12, m.shadow, u)


def _garment_cloak(cv, pose, m):
    u = pose.body_dy
    _r(cv, 15, 17, 11, 20, m.base, u)                                        # mantle over the shoulders
    _r(cv, 15, 16, 11, 14, m.highlight, u); _r(cv, 15, 17, 19, 20, m.shadow, u)
    _r(cv, 18, 26, 10, 11, m.base, u); _r(cv, 18, 26, 20, 21, m.base, u)      # cloak hangs down both sides (2px)
    _r(cv, 18, 26, 10, 10, m.highlight, u); _r(cv, 18, 26, 21, 21, m.shadow, u)
    _r(cv, 27, 28, 10, 12, m.base); _r(cv, 27, 28, 19, 21, m.base)            # pools at the hem
    _r(cv, 27, 28, 20, 21, m.shadow)


def _garment(cv, pose, mats):
    kind = mats.get("garment", "none")
    fn = {"apron": _garment_apron, "scarf": _garment_scarf, "cloak": _garment_cloak}.get(kind)
    if fn is not None:
        fn(cv, pose, Ramp(mats["garment_color"]))


# ---- feet: bare overrides the baked boots with skin (rides the legs) ----
def _feet_bare(cv, pose, skin):
    _r(cv, 28, 29, 12, 14, skin.base, pose.lleg_dy)
    _r(cv, 28, 29, 17, 19, skin.base, pose.rleg_dy)
    _p(cv, 29, 14, skin.shadow, pose.lleg_dy); _p(cv, 29, 17, skin.shadow, pose.rleg_dy)
    _p(cv, 29, 11, skin.base, pose.lleg_dy); _p(cv, 29, 20, skin.base, pose.rleg_dy)  # toes splay out


# ---- arms: stone reinforcement over the exposed forearms/knuckles ----
def _arms_stone(cv, pose, m):
    _r(cv, 18, 21, 10, 10, m.base, pose.larm_dy); _p(cv, 18, 10, m.highlight, pose.larm_dy)
    _r(cv, 18, 21, 21, 21, m.base, pose.rarm_dy); _p(cv, 21, 21, m.shadow, pose.rarm_dy)


# ---- hair accent: sprigs/flowers tucked into the hair (over the hair layer) ----
def _accents(cv, pose, mats):
    if mats.get("hair_accent", "none") != "flora":
        return
    u = pose.body_dy
    herb = Ramp((112, 154, 72))
    _p(cv, 2, 12, herb.base, u); _p(cv, 1, 12, herb.highlight, u)
    _p(cv, 2, 19, herb.base, u); _p(cv, 3, 20, herb.highlight, u)


# ---- prop vocabularies (catalog reads these so the MCP surfaces + validates them) ----
_HELD = ("none", "sword", "dagger", "greatsword", "axe", "spear", "staff", "bow",
         "mace", "wand", "rod", "flamestaff", "shield", "daggers")
_GARMENTS = ("none", "apron", "scarf", "cloak")
_FEET = ("boots", "bare")
_ARMS = ("normal", "stone")
_ACCENTS = ("none", "flora")


def build_frame(contract, config, pose) -> np.ndarray:
    w, h = contract.canvas_of("character")
    mats = {**DEFAULT_CONFIG, **(config or {})}
    skin, hair = Ramp(mats["skin"]), Ramp(mats["hair"])
    shirt, pants = Ramp(mats["shirt"]), Ramp(mats["pants"])
    dark = _sh(mats["hair"], 0.68)                            # shared eye + outline + sole
    cv = Canvas(w, h)
    _base_body(cv, pose, skin)
    _pants(cv, pose, pants, dark)
    if mats.get("feet", "boots") == "bare":
        _feet_bare(cv, pose, skin)                           # over the boots
    _shirt(cv, pose, shirt)
    if mats.get("arms", "normal") == "stone":
        _arms_stone(cv, pose, Ramp(mats["arm_color"]))       # over the forearms
    _garment(cv, pose, mats)                                 # apron/scarf/cloak over the shirt
    _hair(cv, pose, hair, mats.get("hair_style", "short"))
    _accents(cv, pose, mats)                                 # flora over the hair
    _face(cv, pose, dark, skin)
    _beard(cv, pose, hair, mats.get("beard", "none"))        # over the face
    _hat(cv, pose, Ramp(mats["hat_color"]), mats.get("hat", "none"))   # over the crown
    _held(cv, pose, mats)                                    # front-most: staff/shield/etc
    cv.outline(dark)                                         # one shared pass outlines props too
    return cv.array()


def build_humanoid(contract, config=None) -> np.ndarray:
    return build_frame(contract, config, IDLE)


def humanoid_walk(contract, config=None) -> list[np.ndarray]:
    return [build_frame(contract, config, p) for p in WALK]
