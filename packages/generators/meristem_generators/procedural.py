"""Procedural backend (promoted from the Phase 0 bake-off): algorithmic shape
grammar + palette ramps + a uniform top-left bevel. Deterministic, free forever.
Wins the *surfaces* (terrain tiles); weaker on discrete objects (dec-0011)."""
from __future__ import annotations

import numpy as np
from PIL import Image

from .base import (AssetSpec, Generator, TRANSPARENT, new_grid, render,
                   stable_rng, disc, bevel, outline)


def _tile(contract, C, name, base, dark, light, speckle, wave=False, cracks=False, sparkle=None):
    r = stable_rng("proc:" + name)
    w, h = contract.canvas_of("terrain_tile")
    g = new_grid(w, h); g[:] = base
    if speckle:
        g[r.random((h, w)) < speckle] = dark
    if wave:
        for y in range(0, h, 3):
            xs = np.arange(w)
            g[y, (xs + (y // 3)) % 2 == 0] = dark
    if cracks:
        for _ in range(3):
            x = int(r.integers(2, w - 2)); y = int(r.integers(2, h - 2))
            for _ in range(int(r.integers(2, 5))):
                g[y, x] = dark
                x = min(w - 1, max(0, x + int(r.integers(-1, 2)))); y = min(h - 1, y + 1)
    if sparkle is not None:
        for _ in range(2):
            g[int(r.integers(1, h - 1)), int(r.integers(1, w - 1))] = sparkle
    for x in range(w):
        g[0, x] = light; g[h - 1, x] = dark
    for y in range(h):
        g[y, 0] = light; g[y, w - 1] = dark
    return g


def _player(contract, C):
    w, h = contract.canvas_of("character")
    g = new_grid(w, h); cx = w // 2
    skin, tunic, leg = C["peach"], C["blue"], C["brown"]
    disc(g, 10, cx, 4, 4, skin)
    g[15:24, cx - 4:cx + 4] = tunic
    g[16:22, cx - 6:cx - 4] = tunic; g[16:22, cx + 4:cx + 6] = tunic
    g[24:29, cx - 4:cx - 1] = leg; g[24:29, cx + 1:cx + 4] = leg
    g[10, cx - 2] = C["black"]; g[10, cx + 1] = C["black"]
    bevel(g, C["white"], C["dark_grey"])
    outline(g, C["black"])
    return g


def _slime(contract, C):
    w, h = contract.canvas_of("enemy")
    g = new_grid(w, h); cx = w // 2
    base, dark = C["green"], C["dark_green"]
    disc(g, 22, cx, 10, 12, base)
    g[28, cx - 11:cx + 11] = base
    g[20, cx - 4] = C["white"]; g[20, cx + 3] = C["white"]
    g[21, cx - 4] = C["black"]; g[21, cx + 3] = C["black"]
    bevel(g, C["white"], dark)
    outline(g, C["dark_green"])
    return g


def _sword(contract, C):
    w, h = contract.canvas_of("item_icon")
    g = new_grid(w, h)
    blade, grip, guard = C["light_grey"], C["brown"], C["yellow"]
    for i in range(10):
        y = 12 - i; x = 3 + i
        if 0 <= y < h and 0 <= x < w:
            g[y, x] = blade
            if y + 1 < h and x - 1 >= 0:
                g[y + 1, x - 1] = blade
    g[2, 13] = C["white"]
    g[12, 2] = guard; g[13, 3] = guard; g[11, 3] = guard
    g[13, 2] = grip; g[14, 1] = grip
    outline(g, C["dark_grey"])
    return g


def _potion(contract, C):
    w, h = contract.canvas_of("item_icon")
    g = new_grid(w, h)
    glass, liquid, cork = C["light_grey"], C["red"], C["brown"]
    disc(g, 10, 8, 4, 4, liquid)
    g[4:7, 7:10] = glass; g[3, 7:10] = cork; g[7, 5:12] = glass
    g[9, 6] = C["white"]
    outline(g, C["dark_grey"])
    return g


def _key(contract, C):
    w, h = contract.canvas_of("item_icon")
    g = new_grid(w, h)
    gold, dark = C["yellow"], C["orange"]
    disc(g, 5, 5, 3, 3, gold); disc(g, 5, 5, 1.3, 1.3, TRANSPARENT)
    g[6:13, 6:8] = gold; g[11, 8:11] = gold; g[12, 8:10] = gold
    bevel(g, C["yellow"], dark)
    outline(g, C["orange"])
    return g


def _heart(contract, C):
    w, h = contract.canvas_of("ui_element")
    g = new_grid(w, h)
    red, dark = C["red"], C["dark_purple"]
    disc(g, 6, 5, 3, 3, red); disc(g, 6, 10, 3, 3, red)
    for y in range(6, 14):
        half = 7 - (y - 6)
        g[y, max(0, 8 - half):min(w, 8 + half)] = red
    bevel(g, C["pink"], dark)
    g[5, 4] = C["white"]
    outline(g, C["dark_purple"])
    return g


def _coin(contract, C):
    w, h = contract.canvas_of("ui_element")
    g = new_grid(w, h)
    gold, dark = C["yellow"], C["orange"]
    disc(g, 8, 8, 6, 6, gold); disc(g, 8, 8, 4, 4, TRANSPARENT)
    disc(g, 8, 8, 3.2, 3.2, dark); disc(g, 8, 8, 2.2, 2.2, gold)
    bevel(g, C["white"], dark)
    outline(g, C["orange"])
    return g


class ProceduralGenerator(Generator):
    name = "procedural"

    _RECIPES = {
        "grass": lambda c, C: _tile(c, C, "grass", C["green"], C["dark_green"], C["green"], 0.28),
        "dirt":  lambda c, C: _tile(c, C, "dirt", C["brown"], C["dark_grey"], C["brown"], 0.22, cracks=True),
        "water": lambda c, C: _tile(c, C, "water", C["blue"], C["dark_blue"], C["blue"], 0.0, wave=True, sparkle=C["white"]),
        "stone": lambda c, C: _tile(c, C, "stone", C["light_grey"], C["dark_grey"], C["white"], 0.10, cracks=True),
        "player": _player, "slime": _slime, "sword": _sword, "potion": _potion,
        "key": _key, "heart": _heart, "coin": _coin,
    }

    def supports(self, spec: AssetSpec) -> bool:
        return spec.name in self._RECIPES

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        if spec.name not in self._RECIPES:
            raise NotImplementedError(f"procedural backend has no recipe for {spec.name!r}")
        C = contract.name_to_index
        grid = self._RECIPES[spec.name](contract, C)
        return render(grid, contract.palette_rgb)
