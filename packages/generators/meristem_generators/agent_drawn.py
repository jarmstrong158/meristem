"""Agent-drawn backend: coordinate-based sprite builders using the shared
hue-shifted material-ramp standard (dec-0020/0021). Wins the *objects* (character,
enemy, icons, UI) per dec-0011; tiles fall back to the procedural backend.

Every builder draws from named materials, each auto-deriving a 3-shade ramp
(shadow cool / base / highlight warm) with one light direction (top-left) and a
selective outline. See sprite.py (the Canvas toolkit) and shading.py (the ramps).
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .base import AssetSpec, Generator
from .procedural import ProceduralGenerator


HERO_MATERIALS = {          # free-form base colors; ramps derived by hue-shift
    "hair": (112, 68, 40),
    "skin": (232, 176, 136),
    "tunic": (56, 126, 196),
    "pants": (78, 72, 98),
    "boot": (56, 44, 40),
    "belt": (208, 170, 76),
}


def build_hero(contract, materials: dict | None = None) -> np.ndarray:
    """A 32x32 front-facing hero as an RGBA array, using per-material hue-shifted
    ramps (Vanguard style, dec-0020): every material = base + cool shadow + warm
    highlight. Directional light (top-left). Eyes as 1x2 dark dots at cols 13 & 18
    with 4px of skin between; no center blob (docs/research/02-character-sprites.md)."""
    from .shading import Ramp, shadow as _sh
    w, h = contract.canvas_of("character")
    mats = {**HERO_MATERIALS, **(materials or {})}
    hair, skin, tunic = Ramp(mats["hair"]), Ramp(mats["skin"]), Ramp(mats["tunic"])
    pants, belt = Ramp(mats["pants"]), Ramp(mats["belt"])
    # shared shades to stay within the 15-colour budget (style guide): the outline
    # doubles as the eye colour, and boots reuse pants-shadow + the outline dark.
    eye = line = _sh(mats["hair"], 0.68)         # one near-black brown for eyes + outline

    img = np.zeros((h, w, 4), dtype=np.uint8)

    def rect(r0, r1, c0, c1, rgb):
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if 0 <= r < h and 0 <= c < w:
                    img[r, c] = (rgb[0], rgb[1], rgb[2], 255)

    def px(r, c, rgb):
        if 0 <= r < h and 0 <= c < w:
            img[r, c] = (rgb[0], rgb[1], rgb[2], 255)

    # --- face ---
    rect(7, 13, 12, 19, skin.base)
    rect(7, 13, 19, 19, skin.shadow)         # shade side (right)
    rect(13, 13, 13, 18, skin.shadow)        # chin
    px(7, 12, skin.highlight); px(8, 12, skin.highlight)   # lit cheek edge
    rect(9, 10, 13, 13, eye)                 # left eye (1x2)
    rect(9, 10, 18, 18, eye)                 # right eye
    px(12, 15, skin.shadow); px(12, 16, skin.shadow)       # soft mouth, below the eyes

    # --- hair: tapered mass + warm highlight (top-left) + cool hairline shadow ---
    rect(2, 2, 13, 18, hair.base)
    rect(3, 3, 12, 19, hair.base)
    rect(4, 5, 11, 20, hair.base)
    rect(6, 6, 12, 19, hair.base)            # fringe over the brow
    rect(7, 9, 11, 11, hair.base)            # left sideburn
    rect(7, 9, 20, 20, hair.base)            # right sideburn
    rect(2, 3, 13, 15, hair.highlight)       # highlight band, top-left
    px(4, 12, hair.highlight); px(4, 13, hair.highlight)
    rect(3, 6, 19, 20, hair.shadow)          # cool shade down the right
    px(7, 20, hair.shadow); px(8, 20, hair.shadow); px(9, 20, hair.shadow)
    rect(6, 6, 13, 18, hair.shadow)          # hairline cast shadow (fringe underside)

    # --- neck ---
    rect(14, 14, 14, 17, skin.base)
    px(14, 17, skin.shadow)

    # --- torso + arms ---
    rect(15, 21, 12, 19, tunic.base)
    rect(16, 17, 11, 20, tunic.base)         # shoulders
    rect(15, 16, 12, 14, tunic.highlight)    # lit shoulder (top-left)
    rect(15, 21, 19, 19, tunic.shadow)       # shade side
    rect(21, 21, 12, 19, tunic.shadow)       # waist shadow
    rect(15, 20, 10, 10, tunic.base)         # left arm
    rect(15, 20, 21, 21, tunic.shadow)       # right arm (shade side)
    rect(20, 21, 10, 10, skin.base)          # left hand
    rect(20, 21, 21, 21, skin.shadow)        # right hand (shade)
    rect(22, 22, 12, 19, belt.base)

    # --- legs + feet (gap on the col 15/16 seam); boots reuse pants-shadow + outline ---
    rect(23, 28, 12, 14, pants.base)
    rect(23, 28, 17, 19, pants.base)
    rect(23, 28, 14, 14, pants.shadow)       # inner-left shadow
    rect(23, 28, 19, 19, pants.shadow)       # outer-right shadow
    px(23, 12, pants.highlight); px(24, 12, pants.highlight)
    rect(29, 29, 12, 14, pants.shadow)       # boots
    rect(29, 29, 17, 19, pants.shadow)
    px(29, 14, line); px(29, 19, line)       # sole

    _outline_rgba(img, line)
    return img


def _outline_rgba(img: np.ndarray, rgb) -> None:
    """1px dark outline into transparent pixels 4-adjacent to opaque content."""
    op = img[..., 3] == 255
    nbr = np.zeros_like(op)
    nbr[1:, :] |= op[:-1, :]; nbr[:-1, :] |= op[1:, :]
    nbr[:, 1:] |= op[:, :-1]; nbr[:, :-1] |= op[:, 1:]
    edge = nbr & ~op
    img[edge] = (rgb[0], rgb[1], rgb[2], 255)


# ===========================================================================
#  Standard hue-shifted builders (dec-0021): every sprite uses material ramps,
#  directional top-left light, and a selective outline via the shared Canvas.
# ===========================================================================
from .sprite import Canvas, outline_dark
from .shading import Ramp


def build_slime(contract, materials=None):
    body = Ramp((96, 200, 96))                 # green
    cv = Canvas(*contract.canvas_of("enemy"))  # 32x32
    cv.disc(24, 16, 8, 12, body.base)          # wide rounded dome sitting on the ground
    cv.disc(20, 12, 3, 5, body.highlight)      # top-left sheen
    cv.disc(28, 21, 4, 8, body.shadow)         # bottom-right shade
    white, dark = (240, 245, 240), outline_dark(body.base)
    cv.rect(22, 23, 12, 13, white); cv.rect(22, 23, 19, 20, white)   # eyes
    cv.px(23, 12, dark); cv.px(23, 19, dark)                          # pupils
    cv.px(26, 15, body.shadow); cv.px(26, 16, body.shadow)           # small mouth
    cv.outline(dark)
    return cv.array()


def _icon(contract, cls="item_icon"):
    return Canvas(*contract.canvas_of(cls))


def build_sword(contract, materials=None):
    blade, gold, grip = Ramp((176, 184, 198)), Ramp((214, 176, 72)), Ramp((122, 80, 48))
    cv = _icon(contract)
    for i in range(9):                          # diagonal blade, bottom-left -> top-right
        r, c = 11 - i, 4 + i
        cv.px(r, c, blade.base); cv.px(r, c + 1, blade.shadow)
        cv.px(r - 1, c, blade.highlight)        # lit (top-left) edge
    cv.px(2, 12, blade.highlight)               # tip
    cv.rect(11, 12, 3, 6, gold.base); cv.px(11, 3, gold.highlight); cv.px(12, 6, gold.shadow)  # guard
    cv.rect(12, 14, 3, 4, grip.base); cv.px(14, 4, grip.shadow)     # grip
    cv.px(14, 3, gold.base)                     # pommel
    cv.outline(outline_dark((90, 90, 100)))
    return cv.array()


def build_potion(contract, materials=None):
    glass, liquid, cork = Ramp((198, 214, 226)), Ramp((214, 64, 78)), Ramp((132, 92, 56))
    cv = _icon(contract)
    cv.disc(10, 8, 4, 4, liquid.base)           # round flask of liquid
    cv.disc(11, 10, 2, 2, liquid.shadow)        # bottom-right shade
    cv.disc(9, 6, 1.4, 1.6, liquid.highlight)   # top-left sheen
    cv.rect(4, 6, 7, 9, glass.base)             # neck
    cv.px(4, 7, glass.highlight); cv.rect(4, 6, 9, 9, glass.shadow)
    cv.rect(6, 6, 5, 11, glass.base)            # shoulders/rim
    cv.rect(2, 3, 7, 9, cork.base); cv.px(3, 9, cork.shadow)        # cork
    cv.px(8, 6, glass.highlight)                # glass glint over liquid
    cv.outline(outline_dark((70, 80, 96)))
    return cv.array()


def build_key(contract, materials=None):
    gold = Ramp((226, 190, 74))
    cv = _icon(contract)
    cv.disc(5, 5, 3, 3, gold.base)              # bow (ring)
    cv.clear_disc(5, 5, 1.4, 1.4)
    cv.disc(4, 4, 1.2, 1.2, gold.highlight)     # top-left sheen on the bow
    cv.rect(6, 12, 6, 7, gold.base)             # shaft
    cv.rect(6, 12, 7, 7, gold.shadow)           # shaft right-shade
    cv.rect(11, 11, 8, 10, gold.base); cv.rect(12, 12, 8, 9, gold.base)   # teeth
    cv.px(12, 9, gold.shadow)
    cv.outline(outline_dark((150, 110, 30)))
    return cv.array()


def build_heart(contract, materials=None):
    red = Ramp((226, 62, 84))
    cv = Canvas(*contract.canvas_of("ui_element"))   # 16x16
    spans = {4: [(4, 6), (9, 11)], 5: [(3, 12)], 6: [(3, 12)], 7: [(4, 11)],
             8: [(5, 10)], 9: [(6, 9)], 10: [(7, 8)]}
    for r, segs in spans.items():                    # clean heart silhouette
        for c0, c1 in segs:
            cv.rect(r, r, c0, c1, red.base)
    for r, segs in spans.items():                    # shadow: bottom-right half
        if r >= 6:
            for c0, c1 in segs:
                cv.rect(r, r, max(c0, 8), c1, red.shadow)
    cv.rect(4, 5, 4, 5, red.highlight)               # glint on the top-left lobe
    cv.px(4, 4, (255, 240, 245))                      # specular dot
    cv.outline(outline_dark(red.base))
    return cv.array()


def build_coin(contract, materials=None):
    gold = Ramp((240, 206, 84))
    cv = Canvas(*contract.canvas_of("ui_element"))   # 16x16
    circ = {2: (6, 9), 3: (4, 11), 4: (3, 12), 5: (3, 12), 6: (2, 13), 7: (2, 13),
            8: (2, 13), 9: (2, 13), 10: (3, 12), 11: (3, 12), 12: (4, 11), 13: (6, 9)}
    for r, (c0, c1) in circ.items():                 # clean circle silhouette
        cv.rect(r, r, c0, c1, gold.base)
    for r in range(9, 14):                           # bottom-right shade
        c0, c1 = circ[r]
        cv.rect(r, r, (c0 + c1) // 2, c1, gold.shadow)
    cv.rect(3, 4, 4, 6, gold.highlight); cv.px(2, 7, gold.highlight)   # top-left rim
    cv.rect(6, 9, 6, 9, gold.shadow); cv.rect(7, 8, 7, 8, gold.base)   # inner face
    cv.px(4, 5, (255, 248, 210))                     # specular
    cv.outline(outline_dark((170, 130, 30)))
    return cv.array()


_RGBA_BUILDERS = {
    ("character", "player"): build_hero,
    ("enemy", "slime"): build_slime,
    ("item_icon", "sword"): build_sword,
    ("item_icon", "potion"): build_potion,
    ("item_icon", "key"): build_key,
    ("ui_element", "heart"): build_heart,
    ("ui_element", "coin"): build_coin,
}



# --- walk-cycle ops on RGBA arrays (opaque == alpha 255); the character is RGB now ---
_CLEAR = (0, 0, 0, 0)


def _opaque(arr):
    return arr[..., 3] == 255


def _leg_columns(arr) -> tuple[list[int], list[int]]:
    h, w = arr.shape[:2]
    op = _opaque(arr)
    rows = range(max(0, h - 4), h)
    cols = [c for c in range(w) if any(op[r, c] for r in rows)]
    mid = w // 2
    return [c for c in cols if c < mid], [c for c in cols if c >= mid]


def _lift_foot(arr, cols, dy: int = 1):
    if not cols:
        return arr.copy()
    out = arr.copy()
    h = arr.shape[0]
    foot_h, top = 3, arr.shape[0] - 3
    for c in cols:
        for i in range(foot_h):
            src = i + dy
            out[top + i, c] = arr[top + src, c] if src < foot_h else _CLEAR
    return out


def _squash_body(arr, leg_top: int, dy: int = 1):
    out = np.zeros_like(arr)
    out[dy:leg_top + dy, :] = arr[0:leg_top, :]                 # body lowered
    op = out[leg_top:, :, 3] == 255
    out[leg_top:, :] = np.where(op[..., None], out[leg_top:, :], arr[leg_top:, :])
    return out


def _bottom_opaque_row(arr) -> int:
    op = _opaque(arr)
    rows = [r for r in range(arr.shape[0]) if op[r].any()]
    return rows[-1] if rows else arr.shape[0] - 1


def _swing_arms(arr, forward_side: str, dy: int = 1):
    """Swing the two hands in opposition: the hand on `forward_side` down 1px (forward),
    the other up. Only the outermost opaque columns in the hand band are touched."""
    out = arr.copy()
    h, w = arr.shape[:2]
    op = _opaque(arr)
    band = list(range(max(0, h - 12), h - 8))
    cols = [c for c in range(w) if any(op[r, c] for r in band)]
    if not cols:
        return out
    mid = w // 2
    for c in (min(cols), max(cols)):
        d = dy if (("left" if c < mid else "right") == forward_side) else -dy
        colpix = [(r, tuple(arr[r, c])) for r in band if op[r, c]]
        for r in band:
            if op[r, c]:
                out[r, c] = _CLEAR
        for r, val in colpix:
            out[(r + d) if (r + d) in band else r, c] = val
    return out


class AgentDrawnGenerator(Generator):
    name = "agent-drawn"

    def __init__(self):
        self._proc = ProceduralGenerator()

    def supports(self, spec: AssetSpec) -> bool:
        return (spec.asset_class, spec.name) in _RGBA_BUILDERS or self._proc.supports(spec)

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        builder = _RGBA_BUILDERS.get((spec.asset_class, spec.name))
        if builder is not None:                                # hue-shifted RGBA sprite
            return Image.fromarray(builder(contract), "RGBA")
        return self._proc.generate(spec, contract)             # tiles reuse procedural

    def generate_frames(self, spec: AssetSpec, contract) -> list[Image.Image]:
        """4-frame front-facing walk cycle (step-L -> stand -> step-R -> stand) built on
        animation principles: alternating foot lift + 1px body dip + opposed arm swing,
        planted foot locked. See docs/research/01-walk-cycle.md."""
        if spec.asset_class == "character" and spec.variant == "walk":
            idle = build_hero(contract)                        # RGBA
            left_cols, right_cols = _leg_columns(idle)
            leg_top = _bottom_opaque_row(idle) - 6
            f0 = _swing_arms(_lift_foot(_squash_body(idle, leg_top), right_cols), "left")
            f1 = idle
            f2 = _swing_arms(_lift_foot(_squash_body(idle, leg_top), left_cols), "right")
            f3 = idle
            return [Image.fromarray(f, "RGBA") for f in (f0, f1, f2, f3)]
        return [self.generate(spec, contract)]
