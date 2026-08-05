"""Action poses derived from a finished idle frame.

Most archetypes register no frame function, so a generated sheet carried one
pose padded across every column: attacks, hurt reactions and deaths all played
the idle image. This turns that idle into the action bands a Puny-layout sheet
expects, without asking every archetype to draw seven more poses by hand.

Everything here is PIXEL-SAFE and that is the whole design constraint:

  * translation is by whole pixels;
  * lean is a per-row integer shear, never a rotation -- a rotation resamples,
    which invents colours that are not in the sprite's palette and softens
    every edge on a 32px figure;
  * squash removes whole rows rather than scaling;
  * fade multiplies alpha only, so no colour is introduced.

Nothing here reads a palette or a contract, so a pose can never take a sprite
off-model. It can only move pixels the archetype already drew.
"""
from __future__ import annotations

from PIL import Image

RGBA = "RGBA"


# ------------------------------------------------------------------ primitives
def shift(img: Image.Image, dx: int = 0, dy: int = 0) -> Image.Image:
    """Whole-pixel translation on a transparent canvas of the same size."""
    out = Image.new(RGBA, img.size, (0, 0, 0, 0))
    out.paste(img, (int(dx), int(dy)), img)
    return out


def lean(img: Image.Image, amount: int, anchor: float = 1.0) -> Image.Image:
    """Shear horizontally: `amount` px at the top, 0 at the anchor line.

    anchor is a fraction of the height (1.0 = feet stay planted). Each row is
    offset by an INTEGER, so this is a rearrangement of existing pixels rather
    than a rotation -- no resampling, no new colours, no soft edges.
    """
    w, h = img.size
    out = Image.new(RGBA, (w, h), (0, 0, 0, 0))
    base = max(1.0, h * anchor)
    for y in range(h):
        t = 1.0 - min(1.0, y / base)          # 1 at the top, 0 at the anchor
        dx = int(round(amount * t))
        row = img.crop((0, y, w, y + 1))
        out.paste(row, (dx, y), row)
    return out


def squash(img: Image.Image, rows: int) -> Image.Image:
    """Drop `rows` scanlines from the middle and settle the figure downward.

    Removing rows keeps every remaining pixel exactly as drawn. Scaling the
    image to a shorter box would resample it instead.
    """
    if rows <= 0:
        return img.copy()
    w, h = img.size
    keep = Image.new(RGBA, (w, h - rows), (0, 0, 0, 0))
    mid = h // 2
    top = img.crop((0, 0, w, mid - rows // 2))
    bot = img.crop((0, mid + (rows - rows // 2), w, h))
    keep.paste(top, (0, 0), top)
    keep.paste(bot, (0, top.size[1]), bot)
    out = Image.new(RGBA, (w, h), (0, 0, 0, 0))
    out.paste(keep, (0, rows), keep)          # settle down so the feet stay put
    return out


def fade(img: Image.Image, factor: float) -> Image.Image:
    """Scale alpha. Colour channels are untouched, so the palette is preserved."""
    out = img.copy()
    a = out.getchannel("A").point(lambda v: int(v * factor))
    out.putalpha(a)
    return out


# ----------------------------------------------------------------- pose recipes
# Each entry is (dx, dy, lean_px, squash_rows, alpha).
#
# The shapes follow the style guide's 5.2: an action reads as wind-up, strike,
# follow-through. The wind-up leans AWAY from the target so the strike has
# somewhere to travel from -- without it a lunge reads as the sprite teleporting
# forward one pixel.
#
# Sprites face RIGHT when drawn (the Vanguard loader flips them), so +lean is
# toward the enemy.
_SWORD = [
    (0, 0, -2, 0, 1.0),      # wind-up: lean back
    (1, 0, 4, 0, 1.0),       # strike: lunge forward, torso ahead of the feet
    (2, 1, 5, 1, 1.0),       # contact: furthest, settled, one row of squash
    (0, 0, 1, 0, 1.0),       # follow-through: recovering, not yet idle
]
_BOW = [
    (0, 0, -3, 0, 1.0),      # draw
    (1, 0, 2, 0, 1.0),       # release
    (0, 0, 0, 0, 1.0),       # recover
]
_STAVE = [
    (0, -1, 0, 0, 1.0),      # raise: whole figure lifts a pixel
    (0, -2, 1, 0, 1.0),      # cast: peak
    (0, 0, 0, 0, 1.0),       # lower
]
_THROW = [
    (0, 0, -3, 0, 1.0),      # wind
    (2, 0, 4, 0, 1.0),       # release
]
_HURT = [
    (-2, 1, -4, 1, 1.0),     # knocked back and folded; the white flash is a
]                            # runtime tint, not baked into the sheet
# Death topples and sinks; it does not shear apart. At -13px of lean on a 32px
# figure the sprite stopped reading as a falling body and started reading as a
# corrupted one -- and any long vertical prop (Maren's staff) skewed worst of
# all, because a shear moves its top far from its base. Sink and fade carry the
# beat instead, with only enough lean to sell the fall.
_DEATH = [
    (-1, 1, -3, 1, 1.0),     # buckling
    (-1, 4, -5, 4, 0.80),    # going down
    (-2, 8, -7, 8, 0.45),    # down, fading -- alpha only, never a colour wash
]

POSE_BANDS: dict[str, list[tuple]] = {
    "sword": _SWORD,
    "bow": _BOW,
    "stave": _STAVE,
    "throw": _THROW,
    "hurt": _HURT,
    "death": _DEATH,
}


def apply_pose(idle: Image.Image, spec: tuple) -> Image.Image:
    """One (dx, dy, lean_px, squash_rows, alpha) recipe applied to an idle."""
    dx, dy, lean_px, squash_rows, alpha = spec
    out = idle
    if squash_rows:
        out = squash(out, squash_rows)
    if lean_px:
        out = lean(out, lean_px)
    if dx or dy:
        out = shift(out, dx, dy)
    if alpha < 1.0:
        out = fade(out, alpha)
    return out


def pose_band(idle: Image.Image, band: str) -> list[Image.Image]:
    """Every frame of one named band, derived from `idle`."""
    return [apply_pose(idle, spec) for spec in POSE_BANDS[band]]
