"""Agent-drawn backend: hand-authored pixel art as palette-index string grids.

Char legend (palette index): 0 black 1 dark_blue 2 dark_purple 3 dark_green
4 brown 5 dark_grey 6 light_grey 7 white 8 red 9 orange a yellow b green
c blue d lavender e pink f peach ; '.' = transparent.

This is the "agent draws it" backend: authored, then inspected at 8x and refined.
Tiles reuse the procedural backend (procedural wins tiles decisively — see bake-off
results); the 7 sprites below are hand-drawn to test whether a drawn character
coheres with procedural tiles under the same style contract.
"""
from __future__ import annotations

import numpy as np

import lib
import gen_procedural
from lib import new_grid, TRANSPARENT as T

_HEX = "0123456789abcdef"


def _parse(rows: list[str]) -> np.ndarray:
    h = len(rows)
    w = max(len(r) for r in rows)
    g = new_grid(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "." or ch == " ":
                continue
            g[y, x] = _HEX.index(ch)
    return g


def _place(cls: str, rows: list[str], anchor: str = "center") -> np.ndarray:
    """Parse a block and center/anchor it on the class canvas."""
    w, h = lib.canvas_of(cls)
    g = new_grid(w, h)
    block = _parse(rows)
    bh, bw = block.shape
    ox = (w - bw) // 2
    if anchor == "bottom_center":
        oy = h - bh - 1
    else:
        oy = (h - bh) // 2
    for y in range(bh):
        for x in range(bw):
            if block[y, x] >= 0 and 0 <= oy + y < h and 0 <= ox + x < w:
                g[oy + y, ox + x] = block[y, x]
    return g


# ------------------------------------------------------------------ CHARACTER
# 16 wide x 24 tall, front-facing hero. Outline 0, hair 4, face f, tunic c,
# tunic shadow 1, belt/boots 4, hands f, white eyes with black pupils.
CHAR = [
    "....000000....",
    "...04444440...",
    "..0444444440..",
    "..04ffffff40..",
    "..0f7f00f7f0..",   # brow + eye whites
    "..0f0f00f0f0..",   # eyes (pupils)
    "..04ffffff40..",
    "...0ffffff0...",   # chin
    "...0cccccc0...",   # collar
    "..0ccccccccc0.",   # shoulders
    ".0c1ccccccc1c0",   # tunic + shadow sides
    ".0fc1ccccc1cf0",   # hands at sides
    ".0f0c1cccc10f0",
    "..00cc11cc00..",   # belt line
    "...04444440...",   # belt/hips
    "...044..440...",   # legs split
    "...044..440...",
    "...0f4..4f0...",   # knees
    "...044..440...",
    "...044..440...",
    "..0444..4440..",   # boots
    "..0000..0000..",
]

# ------------------------------------------------------------------ SLIME
# 24 wide x 16 tall dome. body b, shadow 3, highlight 7, eyes 7/0, outline 0.
SLIME = [
    "..........00000..........",
    ".......0007bbb7000.......",
    ".....00bbbbbbbbbb00.....",
    "....0bbbbbbbbbbbbbb0....",
    "...0b7bbbbbbbbbbbbbb0...",
    "..0b7bbbb7bbbb7bbbbbb0..",
    "..0bbbbb707bb707bbbbb0..",   # eyes
    ".0bbbbbb000bb000bbbbbb0.",
    ".0bbbbbbbbbbbbbbbbbbbb0.",
    ".0bbbbbbbbbbbbbbbbbbbb0.",
    ".0b3bbbbbbbbbbbbbbbb3b0.",
    ".0b33bbbbbbbbbbbbbb33b0.",
    "0b333bbbbbbbbbbbbbb333b0",
    "0b3333333333333333333 b0",
    "0333333333333333333333 0",
    ".00000000000000000000000",
]

# ------------------------------------------------------------------ SWORD (icon 16)
SWORD = [
    "..........0.....",
    ".........070....",
    "........07670...",
    ".......076760...",
    "......076760....",
    ".....076760.....",
    "....076760......",
    "...076760.......",
    "..0767600.......",
    ".0a9a0.0........",   # guard (yellow)
    "0a9a90..........",   # guard
    ".04440..........",   # grip
    "..0440..........",
    "..0440..........",
    "...00...........",
]

# ------------------------------------------------------------------ POTION (icon 16)
POTION = [
    ".....000....",
    ".....040....",   # cork
    ".....040....",
    "....06660...",   # glass neck
    "....06760...",
    "...0666660..",   # shoulders
    "..066666660.",
    ".06888888660",   # liquid + glass
    ".08888888860",
    ".08878888860",   # highlight
    ".08888888860",
    "..088888880.",
    "...0666660..",
    "....00000...",
]

# ------------------------------------------------------------------ KEY (icon 16)
KEY = [
    "...0000....",
    "..09aa90...",
    ".09a00a90..",
    ".0a0..0a0..",
    ".0a0..0a0..",
    ".09a00a90..",
    "..09aa90...",
    "...0aa0....",
    "...0aa0....",
    "...0aa0....",
    "...0aa090..",
    "...0aa0a0..",   # teeth
    "...0aa090..",
    "...0aa0a0..",
    "....000....",
]

# ------------------------------------------------------------------ HEART (ui 16)
HEART = [
    "..000..000..",
    ".08880008880.",
    "0877800088880",   # highlight glint left lobe
    "088888888888 0",
    "0888888888880",
    "0288888888820",
    ".02888888820.",
    "..028888820..",
    "...0288820...",
    "....02820....",
    ".....020.....",
    "......0......",
]

# ------------------------------------------------------------------ COIN (ui 16)
COIN = [
    "....00000....",
    "..009999900..",
    ".09a9aaaa990.",
    "09a7aaaaaa90.",   # highlight
    "0aa9aaaa9aa0.",
    "0aa9a99a9aa0.",   # inner ring
    "0aa9a99a9aa0.",
    "0aa9aaaa9aa0.",
    "09a9aaaa9a90.",
    ".09aaaaaa90..",
    "..009999000..",
    "....00000....",
]


AUTHORED = {
    "char_player_idle": lambda: _place("character", CHAR, "bottom_center"),
    "enemy_slime_idle": lambda: _place("enemy", SLIME, "bottom_center"),
    "icon_sword": lambda: _place("item_icon", SWORD),
    "icon_potion": lambda: _place("item_icon", POTION),
    "icon_key": lambda: _place("item_icon", KEY),
    "ui_heart": lambda: _place("ui_element", HEART),
    "ui_coin": lambda: _place("ui_element", COIN),
}


def build(stem: str) -> np.ndarray:
    if stem in AUTHORED:
        return AUTHORED[stem]()
    return gen_procedural.build(stem)  # tiles reuse procedural
