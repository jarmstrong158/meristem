"""Procedural backend: algorithmic shape grammar + palette ramps + a uniform
top-left bevel. Deterministic (fixed seed per asset). No model, free forever.

Every asset gets the SAME light treatment (1px highlight top/left, 1px shadow
bottom/right in the material's shades) — a deliberate coherence lever so a set of
independently-generated assets reads as one artist.
"""
from __future__ import annotations

import hashlib

import numpy as np

import lib
from lib import NAME_TO_I as C, new_grid, TRANSPARENT as T


def _rng(name: str) -> np.random.Generator:
    # deterministic per-asset seed (stable across runs, unlike hash())
    seed = int(hashlib.sha256(("proc:" + name).encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


def _bevel(g: np.ndarray, light: int, shadow: int, only_opaque: bool = True) -> None:
    """1px highlight on top/left edges, 1px shadow on bottom/right, following the
    subject's alpha silhouette."""
    h, w = g.shape
    op = g >= 0
    for y in range(h):
        for x in range(w):
            if only_opaque and not op[y, x]:
                continue
            up = (y == 0) or not op[y - 1, x]
            lf = (x == 0) or not op[y, x - 1]
            dn = (y == h - 1) or not op[y + 1, x]
            rt = (x == w - 1) or not op[y, x + 1]
            if up or lf:
                g[y, x] = light
            elif dn or rt:
                g[y, x] = shadow


def _outline(g: np.ndarray, color: int) -> None:
    """Add a 1px dark outline around the silhouette (into transparent border)."""
    h, w = g.shape
    op = g >= 0
    add = []
    for y in range(h):
        for x in range(w):
            if op[y, x]:
                continue
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and op[ny, nx]:
                    add.append((y, x))
                    break
    for y, x in add:
        g[y, x] = color


def _disc(g: np.ndarray, cy, cx, ry, rx, color) -> None:
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    m = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
    g[m] = color


# ------------------------------- TILES ------------------------------------
def _tile(name: str, base: int, dark: int, light: int, speckle_density: float,
          wave: bool = False, cracks: bool = False, sparkle: int | None = None) -> np.ndarray:
    r = _rng(name)
    w, h = lib.canvas_of("terrain_tile")
    g = new_grid(w, h)
    g[:] = base
    # speckle noise (dark)
    noise = r.random((h, w))
    g[noise < speckle_density] = dark
    if wave:  # horizontal dithered wave lines
        for y in range(0, h, 3):
            xs = np.arange(w)
            g[y, (xs + (y // 3)) % 2 == 0] = dark
    if cracks:  # a couple of dark crack strokes
        for _ in range(3):
            x = int(r.integers(2, w - 2)); y = int(r.integers(2, h - 2))
            for _ in range(int(r.integers(2, 5))):
                g[y, x] = dark
                x = min(w - 1, max(0, x + int(r.integers(-1, 2))))
                y = min(h - 1, max(0, y + 1))
    if sparkle is not None:
        for _ in range(2):
            g[int(r.integers(1, h - 1)), int(r.integers(1, w - 1))] = sparkle
    # uniform bevel: top/left get 'light', bottom/right get 'dark'
    for x in range(w):
        g[0, x] = light
        g[h - 1, x] = dark
    for y in range(h):
        g[y, 0] = light
        g[y, w - 1] = dark
    return g


def tile_grass():  return _tile("grass", C["green"], C["dark_green"], C["green"], 0.28)
def tile_dirt():   return _tile("dirt",  C["brown"], C["dark_grey"], C["brown"], 0.22, cracks=True)
def tile_water():  return _tile("water", C["blue"],  C["dark_blue"], C["blue"], 0.0, wave=True, sparkle=C["white"])
def tile_stone():  return _tile("stone", C["light_grey"], C["dark_grey"], C["white"], 0.10, cracks=True)


# ---------------------------- CHARACTER -----------------------------------
def char_player():
    w, h = lib.canvas_of("character")
    g = new_grid(w, h)
    cx = w // 2
    # feet at bottom (bottom_center anchor). Body block ~ y 8..28
    skin, tunic, leg = C["peach"], C["blue"], C["brown"]
    # head
    _disc(g, 10, cx, 4, 4, skin)
    # torso
    g[15:24, cx - 4:cx + 4] = tunic
    # arms
    g[16:22, cx - 6:cx - 4] = tunic
    g[16:22, cx + 4:cx + 6] = tunic
    # legs
    g[24:29, cx - 4:cx - 1] = leg
    g[24:29, cx + 1:cx + 4] = leg
    # eyes
    g[10, cx - 2] = C["black"]; g[10, cx + 1] = C["black"]
    _bevel(g, C["white"], C["dark_grey"])
    _outline(g, lib.outline_index_for([skin, tunic, leg]))
    return g


# ------------------------------ ENEMY -------------------------------------
def enemy_slime():
    w, h = lib.canvas_of("enemy")
    g = new_grid(w, h)
    cx = w // 2
    base, dark = C["green"], C["dark_green"]
    # dome body sitting on the ground
    _disc(g, 22, cx, 10, 12, base)
    g[22:29, :] = np.where(((np.arange(w)[None, :] - cx) ** 2) / 144 <= 1.0, base, g[22:29, :])
    g[g < 0] = T
    # flat bottom
    g[28, cx - 11:cx + 11] = base
    # eyes
    g[20, cx - 4] = C["white"]; g[20, cx + 3] = C["white"]
    g[20, cx - 4] = C["white"]
    g[21, cx - 4] = C["black"]; g[21, cx + 3] = C["black"]
    _bevel(g, C["white"], dark)
    _outline(g, C["dark_green"])
    return g


# ------------------------------ ICONS -------------------------------------
def icon_sword():
    w, h = lib.canvas_of("item_icon")
    g = new_grid(w, h)
    blade, grip, guard = C["light_grey"], C["brown"], C["yellow"]
    # diagonal blade from bottom-left to top-right
    for i in range(10):
        y = 12 - i; x = 3 + i
        if 0 <= y < h and 0 <= x < w:
            g[y, x] = blade
            if y + 1 < h and x - 1 >= 0:
                g[y + 1, x - 1] = blade
    # tip highlight
    g[2, 13] = C["white"]
    # guard
    g[12, 2] = guard; g[13, 3] = guard; g[11, 3] = guard
    # grip
    g[13, 2] = grip; g[14, 1] = grip
    _outline(g, C["dark_grey"])
    return g


def icon_potion():
    w, h = lib.canvas_of("item_icon")
    g = new_grid(w, h)
    glass, liquid, cork = C["light_grey"], C["red"], C["brown"]
    # round flask body
    _disc(g, 10, 8, 4, 4, liquid)
    # neck
    g[4:7, 7:10] = glass
    # cork
    g[3, 7:10] = cork
    # glass rim over liquid top
    g[7, 5:12] = glass
    # highlight glint
    g[9, 6] = C["white"]
    _outline(g, C["dark_grey"])
    return g


def icon_key():
    w, h = lib.canvas_of("item_icon")
    g = new_grid(w, h)
    gold, dark = C["yellow"], C["orange"]
    # bow (ring)
    _disc(g, 5, 5, 3, 3, gold)
    _disc(g, 5, 5, 1.3, 1.3, T)  # hole
    # shaft
    g[6:13, 6:8] = gold
    # teeth
    g[11, 8:11] = gold
    g[12, 8:10] = gold
    _bevel(g, C["yellow"], dark)
    _outline(g, C["orange"])
    return g


# -------------------------------- UI --------------------------------------
def ui_heart():
    w, h = lib.canvas_of("ui_element")
    g = new_grid(w, h)
    red, dark = C["red"], C["dark_purple"]
    # two top lobes + triangle bottom
    _disc(g, 6, 5, 3, 3, red)
    _disc(g, 6, 10, 3, 3, red)
    for y in range(6, 14):
        half = 7 - (y - 6)
        g[y, max(0, 8 - half):min(w, 8 + half)] = red
    g[g == T] = g[g == T]
    _bevel(g, C["pink"], dark)
    g[5, 4] = C["white"]  # glint
    _outline(g, C["dark_purple"])
    return g


def ui_coin():
    w, h = lib.canvas_of("ui_element")
    g = new_grid(w, h)
    gold, dark = C["yellow"], C["orange"]
    _disc(g, 8, 8, 6, 6, gold)
    _disc(g, 8, 8, 4, 4, T)
    _disc(g, 8, 8, 3.2, 3.2, dark)  # inner face
    _disc(g, 8, 8, 2.2, 2.2, gold)
    _bevel(g, C["white"], dark)
    _outline(g, C["orange"])
    return g


BUILDERS = {
    "tile_grass": tile_grass, "tile_dirt": tile_dirt, "tile_water": tile_water, "tile_stone": tile_stone,
    "char_player_idle": char_player, "enemy_slime_idle": enemy_slime,
    "icon_sword": icon_sword, "icon_potion": icon_potion, "icon_key": icon_key,
    "ui_heart": ui_heart, "ui_coin": ui_coin,
}


def build(stem: str) -> np.ndarray:
    return BUILDERS[stem]()
