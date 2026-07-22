"""Agent-drawn backend (promoted from the Phase 0 bake-off): hand-authored pixel
art as palette-index string grids. Wins the *objects* (character, enemy, icons, UI)
per dec-0011. Tiles fall back to the procedural backend.

Legend: 0 black 1 dark_blue 2 dark_purple 3 dark_green 4 brown 5 dark_grey
6 light_grey 7 white 8 red 9 orange a yellow b green c blue d lavender e pink
f peach ; '.' = transparent. (Indices match the PICO-8 contract palette order.)
"""
from __future__ import annotations

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


class AgentDrawnGenerator(Generator):
    name = "agent-drawn"

    def __init__(self):
        self._proc = ProceduralGenerator()

    def supports(self, spec: AssetSpec) -> bool:
        return (spec.asset_class, spec.name) in _BLOCKS or self._proc.supports(spec)

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        key = (spec.asset_class, spec.name)
        if key not in _BLOCKS:
            return self._proc.generate(spec, contract)  # tiles reuse procedural
        rows, anchor = _BLOCKS[key]
        w, h = contract.canvas_of(spec.asset_class)
        grid = place_block(parse_block(rows), w, h, anchor)
        return render(grid, contract.palette_rgb)
