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

from .base import AssetSpec, Generator, render, parse_block, place_block
from .procedural import ProceduralGenerator

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


def _leg_columns(grid) -> tuple[list[int], list[int]]:
    """Split the two legs by the central gap, from the bottom foot rows."""
    h, w = grid.shape
    rows = range(max(0, h - 4), h)
    cols = [c for c in range(w) if any(grid[r, c] >= 0 for r in rows)]
    mid = w // 2
    return [c for c in cols if c < mid], [c for c in cols if c >= mid]


def _lift_foot(grid, cols, dy: int = 1):
    """Raise the foot (bottom rows) of one leg by dy, keeping the planted leg locked."""
    if not cols:
        return grid.copy()
    out = grid.copy()
    h = grid.shape[0]
    foot_h = 3
    top = h - foot_h
    for c in cols:
        for i in range(foot_h):
            src = i + dy
            out[top + i, c] = grid[top + src, c] if src < foot_h else -1
    return out


def _squash_body(grid, leg_top: int, dy: int = 1):
    """Drop the head+torso block by dy while the feet stay planted — the step frame
    is 1px shorter than standing (the weight-recoil dip). Feet do not move."""
    out = np.full_like(grid, -1)
    out[dy:leg_top + dy, :] = grid[0:leg_top, :]          # body lowered
    keep = out[leg_top:, :]
    out[leg_top:, :] = np.where(keep >= 0, keep, grid[leg_top:, :])  # legs/feet stay
    return out


def _bottom_opaque_row(grid) -> int:
    rows = [r for r in range(grid.shape[0]) if (grid[r, :] >= 0).any()]
    return rows[-1] if rows else grid.shape[0] - 1


def _swing_arms(grid, forward_side: str, hand_idx: int):
    """Swing hands in opposition: the hand on `forward_side` moves down 1px (forward),
    the other up 1px (back). Operates only on hand-colored pixels in the hand band, so
    it never disturbs the torso or face."""
    if hand_idx is None:
        return grid
    out = grid.copy()
    h, w = grid.shape
    mid = w // 2
    band = range(max(0, h - 12), h - 8)          # hand rows only (excludes face + legs)
    hands = [(r, c) for r in band for c in range(w) if grid[r, c] == hand_idx]
    for r, c in hands:
        side = "left" if c < mid else "right"
        dy = 1 if side == forward_side else -1    # forward = down, back = up
        out[r, c] = -1
        nr = r + dy
        if 0 <= nr < h:
            out[nr, c] = hand_idx
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
        grid = self._grid(spec, contract)
        if grid is None:
            return self._proc.generate(spec, contract)  # tiles reuse procedural
        return render(grid, contract.palette_rgb)

    def generate_frames(self, spec: AssetSpec, contract) -> list[Image.Image]:
        """A 4-frame front-facing walk cycle, built on animation principles (not a
        sideways slide): contact-left -> passing -> contact-right -> passing.
        Alternating single-foot lift + 1px body bob + opposed arm swing; the planted
        foot stays locked. See docs/research/01-walk-cycle.md."""
        if spec.variant == "walk":
            idle = self._grid(spec, contract)
            if idle is not None:
                left_cols, right_cols = _leg_columns(idle)
                leg_top = _bottom_opaque_row(idle) - 6           # legs ~ bottom 7 rows
                # Standing/idle is the TALL neutral. Step frames are 1px shorter (body
                # dips onto the planted foot) with the OTHER foot lifted. Feet stay
                # planted otherwise. Play: step-L -> stand -> step-R -> stand.
                hand = contract.name_to_index.get("peach")
                # opposition: screen-RIGHT foot steps -> screen-LEFT hand forward, & vice versa
                f0 = _swing_arms(_lift_foot(_squash_body(idle, leg_top), right_cols), "left", hand)
                f1 = idle                                                 # passing/standing
                f2 = _swing_arms(_lift_foot(_squash_body(idle, leg_top), left_cols), "right", hand)
                f3 = idle                                                 # passing/standing
                pal = contract.palette_rgb
                return [render(g, pal) for g in (f0, f1, f2, f3)]
        return [self.generate(spec, contract)]
