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
from .sprite import Canvas, translate as _translate


@dataclass
class Pose:
    """Skeleton state for one frame: vertical offsets per region (front view)."""
    body_dy: int = 0        # head + neck + torso (and hair/face, which ride the head)
    larm_dy: int = 0        # left arm swing (added to body_dy)
    rarm_dy: int = 0        # right arm swing
    lleg_dy: int = 0        # left leg / foot lift
    rleg_dy: int = 0        # right leg / foot lift


# Which way the character is looking. A top-down game moves in four directions and
# until now every archetype drew ONE front view, so a character walking north showed
# you its face -- true of Meristem's own compiled games as much as of anything built
# on them.
#
# `west` is never drawn: it is `east` mirrored, which is both half the work and a
# guarantee the two profiles cannot drift apart.
FACINGS = ("south", "north", "east", "west")
DEFAULT_FACING = "south"


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
    "facing": DEFAULT_FACING,    # south · north · east · west (west = mirrored east)
}


def _r(cv: Canvas, r0, r1, c0, c1, rgb, dy=0):
    cv.rect(r0 + dy, r1 + dy, c0, c1, rgb)


def _p(cv: Canvas, r, c, rgb, dy=0):
    cv.px(r + dy, c, rgb)


def _blit(cv: Canvas, arr) -> None:
    """Composite an opaque scratch layer onto the canvas."""
    op = arr[..., 3] == 255
    cv.img[op] = arr[op]


def _shifted(cv: Canvas, dx: int, draw) -> None:
    """Run `draw` on a scratch layer, then slide it in.

    The profile view moves the head and hands to columns the south-authored prop
    layers know nothing about. Re-authoring every hat and weapon in profile would be
    a lot of pixels for a 1x view; shifting the layer they already draw is not.
    """
    layer = Canvas(cv.w, cv.h)
    draw(layer)
    _blit(cv, _translate(layer.array(), dx=dx))


# ---- layers (drawn low z -> high z); each reads the shared pose ----
def _base_body(cv, pose, skin, facing="south"):
    u = pose.body_dy
    if facing == "east":
        # Profile. What sells a side view is the SILHOUETTE, not the shading: the head
        # overhangs the torso forward and ends in a nose, the hair mass overhangs it
        # backward (drawn by _hair), and the near arm stands clear of the trunk while
        # the far one is a sliver behind it. A narrowed front view reads as a smudge.
        _r(cv, 7, 12, 14, 20, skin.base, u)                  # skull
        _r(cv, 13, 13, 14, 19, skin.base, u)                 # jaw, pulled back off the nose
        _r(cv, 10, 11, 21, 21, skin.base, u)                 # nose
        _p(cv, 11, 21, skin.shadow, u)                       # under the tip
        _r(cv, 14, 14, 16, 18, skin.base, u)                 # neck
        _r(cv, 15, 22, 14, 19, skin.base, u)                 # torso
        _r(cv, 15, 19, 13, 13, skin.shadow, u + pose.larm_dy)   # far shoulder, behind
        _r(cv, 15, 21, 20, 21, skin.base, u + pose.rarm_dy)     # near arm, clear of the trunk
        _r(cv, 20, 21, 20, 21, skin.shadow, u + pose.rarm_dy)   # hand
        _r(cv, 23, 29, 14, 16, skin.shadow, pose.lleg_dy)    # far leg
        _r(cv, 23, 29, 17, 19, skin.base, pose.rleg_dy)      # near leg
        return
    _r(cv, 7, 13, 12, 19, skin.base, u)                      # face
    _r(cv, 14, 14, 14, 17, skin.base, u)                     # neck
    _r(cv, 15, 22, 12, 19, skin.base, u)                     # torso (under shirt)
    _r(cv, 15, 21, 10, 10, skin.base, u + pose.larm_dy)      # left arm (under sleeve)
    _r(cv, 15, 21, 21, 21, skin.base, u + pose.rarm_dy)      # right arm
    _r(cv, 20, 21, 10, 10, skin.base, u + pose.larm_dy)      # left hand
    _r(cv, 20, 21, 21, 21, skin.shadow, u + pose.rarm_dy)    # right hand (shade side)
    _r(cv, 23, 29, 12, 14, skin.base, pose.lleg_dy)          # legs (under pants)
    _r(cv, 23, 29, 17, 19, skin.base, pose.rleg_dy)


def _pants(cv, pose, pants, dark, facing="south"):
    legs = (((14, 16), pose.lleg_dy), ((17, 19), pose.rleg_dy)) if facing == "east" \
        else (((12, 14), pose.lleg_dy), ((17, 19), pose.rleg_dy))
    if facing == "east":
        for (c0, c1), dy in legs:
            # the far leg is wholly in shade, which is what keeps the two from
            # merging into one slab when they overlap at rest
            _r(cv, 23, 28, c0, c1, pants.base if c0 == 17 else pants.shadow, dy)
            _r(cv, 29, 29, c0, c1, pants.shadow, dy)         # boot
            _p(cv, 29, c1, dark, dy)                         # sole
        return
    for cols, dy in legs:
        c0, c1 = cols
        _r(cv, 23, 28, c0, c1, pants.base, dy)
        _r(cv, 23, 28, c1 if c0 == 12 else c0, c1 if c0 == 12 else c0, pants.shadow, dy)  # inner/outer shade
        _r(cv, 29, 29, c0, c1, pants.shadow, dy)             # boot
        _p(cv, 29, c1 if c0 == 12 else c0, dark, dy)         # sole
    _p(cv, 23, 12, pants.highlight, pose.lleg_dy)


def _shirt(cv, pose, shirt, facing="south"):
    u = pose.body_dy
    if facing == "east":
        _r(cv, 15, 21, 14, 19, shirt.base, u)                # narrower torso
        _r(cv, 16, 17, 13, 20, shirt.base, u)                # shoulders
        _r(cv, 15, 16, 14, 16, shirt.highlight, u)           # lit top-left
        _r(cv, 15, 21, 19, 19, shirt.shadow, u)              # leading edge falls away
        _r(cv, 21, 21, 14, 19, shirt.shadow, u)              # waist
        _r(cv, 15, 19, 13, 13, shirt.shadow, u + pose.larm_dy)   # far sleeve
        _r(cv, 15, 19, 20, 21, shirt.base, u + pose.rarm_dy)     # near sleeve
        _r(cv, 15, 19, 21, 21, shirt.shadow, u + pose.rarm_dy)
        return
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


# Long hair and a ponytail are the two styles with a SIDE FALL, and a side fall is
# the one hair feature that cannot survive the profile view unchanged: drawn at its
# front-view column it hangs straight across the face. In profile it goes behind.
def _hair_long(cv, u, hair, facing="south"):
    _hair_short(cv, u, hair)                                                   # same cap on top
    if facing == "east":
        _r(cv, 7, 18, 9, 11, hair.base, u)                                     # one fall, behind
        _r(cv, 8, 18, 9, 9, hair.highlight, u)                                 # lit trailing edge
        _r(cv, 18, 18, 9, 11, hair.shadow, u)                                  # tip
        return
    _r(cv, 7, 18, 10, 11, hair.base, u); _r(cv, 7, 18, 20, 21, hair.base, u)  # falls past shoulders
    _r(cv, 8, 18, 10, 10, hair.highlight, u)                                   # lit left fall
    _r(cv, 8, 18, 21, 21, hair.shadow, u)                                      # shaded right fall
    _r(cv, 18, 18, 10, 11, hair.shadow, u); _r(cv, 18, 18, 20, 21, hair.shadow, u)   # tips


def _hair_ponytail(cv, u, hair, facing="south"):
    _hair_short(cv, u, hair)
    if facing == "east":
        _r(cv, 5, 6, 9, 11, hair.base, u); _r(cv, 7, 14, 9, 10, hair.base, u)  # tail off the back
        _r(cv, 7, 14, 9, 9, hair.highlight, u); _p(cv, 6, 11, hair.shadow, u)
        return
    _r(cv, 5, 6, 20, 22, hair.base, u); _r(cv, 7, 14, 21, 22, hair.base, u)   # tail down the right
    _r(cv, 7, 14, 22, 22, hair.shadow, u); _p(cv, 6, 21, hair.highlight, u)


def _hair_spiky(cv, u, hair):
    for c in (11, 13, 15, 17, 19):
        _r(cv, 1, 3, c, c, hair.base, u)                                      # upright spikes
    _r(cv, 4, 5, 11, 20, hair.base, u); _r(cv, 6, 6, 12, 19, hair.base, u)    # base mass
    _r(cv, 7, 9, 11, 11, hair.base, u); _r(cv, 7, 9, 20, 20, hair.base, u)    # sideburns
    _p(cv, 2, 13, hair.highlight, u); _p(cv, 2, 15, hair.highlight, u)
    _r(cv, 4, 6, 19, 20, hair.shadow, u); _r(cv, 6, 6, 13, 18, hair.shadow, u)


_HAIR = {"short": lambda cv, u, hair, f: _hair_short(cv, u, hair),
         "long": _hair_long, "ponytail": _hair_ponytail,
         "spiky": lambda cv, u, hair, f: _hair_spiky(cv, u, hair),
         "bald": lambda cv, u, hair, f: None}


def _hair(cv, pose, hair, style, facing="south"):
    u = pose.body_dy
    _HAIR.get(style, _HAIR["short"])(cv, u, hair, facing)
    if style == "bald":
        return
    if facing == "north":
        # From behind, hair covers the whole skull down to the neck -- there is no
        # face for it to stop at. This is the other half of what sells `north`.
        _r(cv, 7, 12, 12, 19, hair.base, u)
        _r(cv, 7, 12, 19, 19, hair.shadow, u)                # cool shade side
        _r(cv, 7, 8, 12, 14, hair.highlight, u)              # lit crown (top-left)
    elif facing == "east":
        # The mass swings to the trailing side and overhangs the back of the torso.
        # _face clears the leading temple afterwards, so the brow and nose have
        # somewhere to sit -- that pair of overhangs is the whole profile read.
        _r(cv, 6, 13, 11, 14, hair.base, u)                  # back of the head
        _r(cv, 6, 13, 11, 11, hair.highlight, u)             # lit trailing edge (top-left)
        _r(cv, 6, 7, 15, 19, hair.base, u)                   # crown over the skull
        _r(cv, 13, 13, 12, 14, hair.shadow, u)               # nape


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


def _hat(cv, pose, hat, style, facing="south"):
    fn = _HATS.get(style, _HATS["none"])
    if facing == "east":
        # every hat is centred on the front-view head (col 15.5); the profile skull
        # sits two columns forward
        _shifted(cv, 2, lambda layer: fn(layer, pose.body_dy, hat))
        return
    fn(cv, pose.body_dy, hat)


def _face(cv, pose, eye, skin, facing="south"):
    u = pose.body_dy
    # Facing away, you see the back of a head: no eyes, no mouth. This single
    # omission is most of what makes `north` read as north.
    if facing == "north":
        return
    if facing == "east":
        _r(cv, 7, 12, 19, 20, skin.base, u)                                   # clear the leading
        _p(cv, 8, 20, skin.shadow, u)                                         # temple: brow ridge
        _r(cv, 9, 10, 18, 18, eye, u)                                         # one eye
        _p(cv, 12, 20, skin.shadow, u)                                        # mouth at the edge
        return
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
    _r(cv, 8, 24, 23, 23, m.base, dy); _p(cv, 9, 23, m.highlight, dy)         # haft (clear of the head)
    for r, (c0, c1) in {8: (24, 26), 9: (24, 27), 10: (24, 27), 11: (25, 26)}.items():
        _r(cv, r, r, c0, c1, st.base, dy)                   # blade head, flared RIGHT of the haft
    _p(cv, 8, 24, st.highlight, dy); _p(cv, 10, 27, st.shadow, dy)


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
    _r(cv, 13, 21, 24, 24, m.base, dy)                      # handle (clear of the head)
    for r, c in [(6, 24), (8, 21), (8, 27), (12, 22), (12, 26)]:
        cv.line(10 + dy, 24, r + dy, c, st.shadow)          # spikes from the ball centre
    cv.disc(10 + dy, 24, 2.4, 2.4, st.base)                 # ball over the spike roots
    cv.disc(9 + dy, 23, 0.9, 0.9, st.highlight)


def _held_bow(cv, pose, m):
    dy = pose.body_dy + pose.rarm_dy
    # a tall bow at the hand (rows 12-28), limb bulging right, clear of the head
    limb = {12: 23, 13: 24, 14: 25, 15: 25, 16: 26, 17: 26, 18: 26, 19: 26,
            20: 26, 21: 26, 22: 26, 23: 25, 24: 25, 25: 24, 26: 23}
    for r, c in limb.items():
        _p(cv, r, c, m.base, dy); _p(cv, r, c + 1, m.shadow, dy)   # 2px limb
    _r(cv, 13, 25, 23, 23, Ramp(_H_STEEL).highlight, dy)    # taut string (near side)
    _r(cv, 19, 20, 24, 25, m.highlight, dy)                 # wrapped grip at the hand


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


# Every prop above is authored against the SOUTH pose, where the two hands sit at
# col 8 and col 22. The profile body is narrower and both hands collapse onto the
# leading side, so a prop drawn at its south column would float clear of the figure.
# Rather than re-author thirteen weapons in profile, each declares how far to slide.
# A shaft at the profile hand column would run straight down the face, so the long
# poles clear the nose entirely; a shield still covers the trunk, which is what a
# shield does. Everything else already rides col 22, just past the near hand.
_HELD_EAST_DX = {"staff": 14, "flamestaff": 14, "shield": 12, "daggers": 12}
_HELD_EAST_DROP = {"daggers": 16}     # profile hides the far hand: drop its twin


def _held(cv, pose, mats, facing="south"):
    kind = mats.get("held", "none")
    fn = _HELD_FNS.get(kind)
    if fn is None:
        return
    m = Ramp(mats["held_color"])
    if facing != "east":
        fn(cv, pose, m)
        return
    layer = Canvas(cv.w, cv.h)                               # scratch, so the shift is local
    fn(layer, pose, m)
    arr = layer.array()
    drop = _HELD_EAST_DROP.get(kind)
    if drop is not None:
        arr[:, drop:] = 0
    arr = _translate(arr, dx=_HELD_EAST_DX.get(kind, 0))     # default: already at col 22
    _blit(cv, arr)


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


def _garment_cloak(cv, pose, m, facing="south"):
    u = pose.body_dy
    if facing == "east":
        # In profile a cloak reads as ONE mass behind the figure, not two side falls.
        _r(cv, 15, 17, 13, 20, m.base, u)                                    # mantle
        _r(cv, 15, 16, 13, 15, m.highlight, u); _r(cv, 15, 17, 20, 20, m.shadow, u)
        _r(cv, 18, 26, 12, 14, m.base, u)                                    # hangs off the back
        _r(cv, 18, 26, 12, 12, m.highlight, u); _r(cv, 18, 26, 14, 14, m.shadow, u)
        _r(cv, 27, 28, 12, 15, m.base); _r(cv, 27, 28, 14, 15, m.shadow)     # pools at the hem
        return
    _r(cv, 15, 17, 11, 20, m.base, u)                                        # mantle over the shoulders
    _r(cv, 15, 16, 11, 14, m.highlight, u); _r(cv, 15, 17, 19, 20, m.shadow, u)
    _r(cv, 18, 26, 10, 11, m.base, u); _r(cv, 18, 26, 20, 21, m.base, u)      # cloak hangs down both sides (2px)
    _r(cv, 18, 26, 10, 10, m.highlight, u); _r(cv, 18, 26, 21, 21, m.shadow, u)
    _r(cv, 27, 28, 10, 12, m.base); _r(cv, 27, 28, 19, 21, m.base)            # pools at the hem
    _r(cv, 27, 28, 20, 21, m.shadow)


def _garment(cv, pose, mats, facing="south"):
    kind = mats.get("garment", "none")
    if kind not in ("cloak", "apron", "scarf"):
        return
    m = Ramp(mats["garment_color"])
    if kind == "cloak":
        _garment_cloak(cv, pose, m, facing)
        return
    fn = _garment_apron if kind == "apron" else _garment_scarf
    if facing == "east":
        # both are authored on the front-view torso, which sits two columns back
        _shifted(cv, 2, lambda layer: fn(layer, pose, m))
        return
    fn(cv, pose, m)


# ---- feet: bare overrides the baked boots with skin (rides the legs) ----
def _feet_bare(cv, pose, skin, facing="south"):
    lc, rc = ((14, 17) if facing == "east" else (12, 17))
    _r(cv, 28, 29, lc, lc + 2, skin.base, pose.lleg_dy)
    _r(cv, 28, 29, rc, rc + 2, skin.base, pose.rleg_dy)
    _p(cv, 29, lc + 2, skin.shadow, pose.lleg_dy); _p(cv, 29, rc, skin.shadow, pose.rleg_dy)
    if facing == "east":
        _p(cv, 29, rc + 3, skin.base, pose.rleg_dy)          # toes point the way we walk
        return
    _p(cv, 29, lc - 1, skin.base, pose.lleg_dy); _p(cv, 29, rc + 3, skin.base, pose.rleg_dy)


# ---- arms: stone reinforcement over the exposed forearms/knuckles ----
def _arms_stone(cv, pose, m, facing="south"):
    lc, rc = ((13, 21) if facing == "east" else (10, 21))
    _r(cv, 18, 21, lc, lc, m.base, pose.larm_dy); _p(cv, 18, lc, m.highlight, pose.larm_dy)
    _r(cv, 18, 21, rc, rc, m.base, pose.rarm_dy); _p(cv, 21, rc, m.shadow, pose.rarm_dy)


# ---- hair accent: sprigs/flowers tucked into the hair (over the hair layer) ----
def _accents(cv, pose, mats, facing="south"):
    if mats.get("hair_accent", "none") != "flora":
        return
    u = pose.body_dy
    herb = Ramp((112, 154, 72))
    if facing == "east":
        # in profile both sprigs are on the side of the head you can see
        _p(cv, 2, 12, herb.base, u); _p(cv, 1, 12, herb.highlight, u)
        _p(cv, 3, 15, herb.base, u); _p(cv, 2, 16, herb.highlight, u)
        return
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
    facing = mats.get("facing", DEFAULT_FACING)
    if facing not in FACINGS:
        facing = DEFAULT_FACING
    # west is east, mirrored. Drawing it separately would let the two profiles drift.
    draw_facing = "east" if facing == "west" else facing
    skin, hair = Ramp(mats["skin"]), Ramp(mats["hair"])
    shirt, pants = Ramp(mats["shirt"]), Ramp(mats["pants"])
    dark = _sh(mats["hair"], 0.68)                            # shared eye + outline + sole
    cv = Canvas(w, h)
    _base_body(cv, pose, skin, draw_facing)
    _pants(cv, pose, pants, dark, draw_facing)
    if mats.get("feet", "boots") == "bare":
        _feet_bare(cv, pose, skin, draw_facing)              # over the boots
    _shirt(cv, pose, shirt, draw_facing)
    if mats.get("arms", "normal") == "stone":
        _arms_stone(cv, pose, Ramp(mats["arm_color"]), draw_facing)   # over the forearms
    _garment(cv, pose, mats, draw_facing)                    # apron/scarf/cloak over the shirt
    _hair(cv, pose, hair, mats.get("hair_style", "short"), draw_facing)
    _accents(cv, pose, mats, draw_facing)                    # flora over the hair
    _face(cv, pose, dark, skin, draw_facing)
    # a beard is a front-of-face feature; from behind there is nothing to draw
    if draw_facing != "north":
        _beard(cv, pose, hair, mats.get("beard", "none"))
    _hat(cv, pose, Ramp(mats["hat_color"]), mats.get("hat", "none"), draw_facing)
    _held(cv, pose, mats, draw_facing)                       # front-most: staff/shield/etc
    cv.outline(dark)                                         # one shared pass outlines props too
    out = cv.array()
    return out[:, ::-1].copy() if facing == "west" else out


def build_humanoid(contract, config=None) -> np.ndarray:
    return build_frame(contract, config, IDLE)


def humanoid_walk(contract, config=None) -> list[np.ndarray]:
    return [build_frame(contract, config, p) for p in WALK]


def humanoid_facings(contract, config=None) -> dict[str, list[np.ndarray]]:
    """The walk cycle in every facing: {facing: [frames]}.

    What a top-down game actually needs -- one call gives a full directional sheet
    instead of the caller re-deriving which config key to flip."""
    cfg = dict(config or {})
    return {f: [build_frame(contract, {**cfg, "facing": f}, p) for p in WALK]
            for f in FACINGS}
