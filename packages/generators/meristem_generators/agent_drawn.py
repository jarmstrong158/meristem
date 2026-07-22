"""Agent-drawn backend (promoted from the Phase 0 bake-off): hand-authored pixel
art as palette-index string grids. Wins the *objects* (character, enemy, icons, UI)
per dec-0011. Tiles fall back to the procedural backend.

Legend: 0 black 1 dark_blue 2 dark_purple 3 dark_green 4 brown 5 dark_grey
6 light_grey 7 white 8 red 9 orange a yellow b green c blue d lavender e pink
f peach ; '.' = transparent. (Indices match the PICO-8 contract palette order.)
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .base import AssetSpec, Generator, render, parse_block, place_block, outline, new_grid
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

CHAR = [
    "....000000....", "...04444440...", "..0444444440..", "..04ffffff40..",
    "..0f7f00f7f0..", "..0f0f00f0f0..", "..04ffffff40..", "...0ffffff0...",
    "...0cccccc0...", "..0ccccccccc0.", ".0c1ccccccc1c0", ".0fc1ccccc1cf0",
    ".0f0c1cccc10f0", "..00cc11cc00..", "...04444440...", "...044..440...",
    "...044..440...", "...0f4..4f0...", "...044..440...", "...044..440...",
    "..0444..4440..", "..0000..0000..",
]
SLIME = [
    "..........00000..........", ".......0007bbb7000.......", ".....00bbbbbbbbbb00.....",
    "....0bbbbbbbbbbbbbb0....", "...0b7bbbbbbbbbbbbbb0...", "..0b7bbbb7bbbb7bbbbbb0..",
    "..0bbbbb707bb707bbbbb0..", ".0bbbbbb000bb000bbbbbb0.", ".0bbbbbbbbbbbbbbbbbbbb0.",
    ".0bbbbbbbbbbbbbbbbbbbb0.", ".0b3bbbbbbbbbbbbbbbb3b0.", ".0b33bbbbbbbbbbbbbb33b0.",
    "0b333bbbbbbbbbbbbbb333b0", "0b33333333333333333333b0", "03333333333333333333330",
    ".0000000000000000000000.",
]
SWORD = [
    "..........0.....", ".........070....", "........07670...", ".......076760...",
    "......076760....", ".....076760.....", "....076760......", "...076760.......",
    "..0767600.......", ".0a9a0.0........", "0a9a90..........", ".04440..........",
    "..0440..........", "..0440..........", "...00...........",
]
POTION = [
    ".....000....", ".....040....", ".....040....", "....06660...", "....06760...",
    "...0666660..", "..066666660.", ".06888888660", ".08888888860", ".08878888860",
    ".08888888860", "..088888880.", "...0666660..", "....00000...",
]
KEY = [
    "...0000....", "..09aa90...", ".09a00a90..", ".0a0..0a0..", ".0a0..0a0..",
    ".09a00a90..", "..09aa90...", "...0aa0....", "...0aa0....", "...0aa0....",
    "...0aa090..", "...0aa0a0..", "...0aa090..", "...0aa0a0..", "....000....",
]
HEART = [
    "..000..000..", ".08880008880.", "0877800088880", "0888888888880", "0888888888880",
    "0288888888820", ".02888888820.", "..028888820..", "...0288820...", "....02820....",
    ".....020.....", "......0......",
]
COIN = [
    "....00000....", "..009999900..", ".09a9aaaa990.", "09a7aaaaaa90.", "0aa9aaaa9aa0.",
    "0aa9a99a9aa0.", "0aa9a99a9aa0.", "0aa9aaaa9aa0.", "09a9aaaa9a90.", ".09aaaaaa90..",
    "..009999000..", "....00000....",
]

_BLOCKS = {
    ("character", "player"): (CHAR, "bottom_center"),
    ("enemy", "slime"): (SLIME, "bottom_center"),
    ("item_icon", "sword"): (SWORD, "center"),
    ("item_icon", "potion"): (POTION, "center"),
    ("item_icon", "key"): (KEY, "center"),
    ("ui_element", "heart"): (HEART, "center"),
    ("ui_element", "coin"): (COIN, "center"),
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
        return (spec.asset_class, spec.name) in _BLOCKS or self._proc.supports(spec)

    def _grid(self, spec: AssetSpec, contract):
        key = (spec.asset_class, spec.name)
        if key not in _BLOCKS:
            return None
        rows, anchor = _BLOCKS[key]
        w, h = contract.canvas_of(spec.asset_class)
        return place_block(parse_block(rows), w, h, anchor)

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        if spec.asset_class == "character":                    # RGB hue-shifted hero
            return Image.fromarray(build_hero(contract), "RGBA")
        grid = self._grid(spec, contract)
        if grid is None:
            return self._proc.generate(spec, contract)         # tiles reuse procedural
        return render(grid, contract.palette_rgb)

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
