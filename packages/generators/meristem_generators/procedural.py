"""Procedural backend: algorithmic material *tiles* with hue-shifted ramp texture.

Per dec-0011 procedural owns surfaces (terrain tiles); per dec-0021 it uses the same
material-ramp standard as everything else. Texture is speckle/ripple in the ramp's
shadow + highlight shades — NOT a directional bevel — so tiles stay seamlessly
tileable (dec-0012). Deterministic (fixed seed per tile)."""
from __future__ import annotations

import hashlib

import numpy as np
from PIL import Image

from .base import AssetSpec, Generator
from .shading import Ramp

TILE_MATERIALS = {
    "grass": (96, 180, 84),
    "dirt": (150, 108, 68),
    "water": (64, 124, 204),
    "stone": (150, 150, 160),
    "sand": (214, 194, 138),
    "snow": (226, 232, 242),
    "lava": (216, 96, 44),
    "brick": (168, 96, 82),
}


# Course spacing for the two banded materials. These MUST divide the tile height or
# the bands collide across the seam: `_wave` used a hardcoded step of 3 into a 16px
# tile, putting courses at rows 0,3,6,9,12,15 so the last sat 1px from the next
# tile's first, and the water banded visibly at every boundary. Named, so the
# invariant is assertable (see test_periodic_tile_features_divide_the_tile).
WAVE_PERIOD = 4
RIPPLE_PERIOD = 4


def _rng(name: str) -> np.random.Generator:
    seed = int(hashlib.sha256(("proc:" + name).encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


# --- wrap-safe drawing primitives -------------------------------------------------
# A tile is a TORUS. Every feature below writes through _put, so a stroke that runs
# off one edge re-enters on the opposite one. The crack walk used to CLAMP instead
# (`min(w-1, max(0, x))`), which both piled pixels up against the border and showed
# as a repeating dark smudge once the tile was actually laid out — visible in any
# 3x3 preview of `stone`. Clamping is the bug; wrapping is the fix.
def _put(img: np.ndarray, y: int, x: int, rgb) -> None:
    h, w = img.shape[:2]
    img[y % h, x % w] = (*rgb, 255)


def _disc(img: np.ndarray, cy: int, cx: int, rad: float, rgb) -> None:
    ri = int(np.ceil(rad))
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if dy * dy + dx * dx <= rad * rad:
                _put(img, cy + dy, cx + dx, rgb)


# --- structural features ----------------------------------------------------------
# Speckle alone cannot tell two materials apart: grass, dirt, sand, snow and stone
# were one white-noise field at five densities and five hues, so every soft surface
# read as the same gravel. Each of these gives a material its own STRUCTURE.
def _blades(img, ramp, r, n):
    """Grass: upright blades, dark with a lit tip."""
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = int(r.integers(0, w)), int(r.integers(0, h))
        for k in range(int(r.integers(2, 4))):
            _put(img, y + k, x, ramp.shadow)
        _put(img, y - 1, x, ramp.highlight)


def _pebbles(img, ramp, r, n):
    """Dirt: small stones half-buried in the soil."""
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = int(r.integers(0, w)), int(r.integers(0, h))
        _put(img, y, x, ramp.shadow); _put(img, y, x + 1, ramp.shadow)
        _put(img, y - 1, x, ramp.highlight)


def _cracks(img, ramp, r, n):
    """Stone: fissures with a lit upper lip, so the surface reads as fractured plate.
    Each crack picks its own dominant axis — a walk that always steps y+1 lays every
    fissure on the same diagonal, which shows up as corduroy once the tile repeats."""
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = int(r.integers(0, w)), int(r.integers(0, h))
        vertical = bool(r.integers(0, 2))
        for _ in range(int(r.integers(4, 9))):
            _put(img, y, x, ramp.shadow)
            _put(img, y - 1, x, ramp.highlight)
            if vertical:
                y += 1; x += int(r.integers(-1, 2))
            else:
                x += 1; y += int(r.integers(-1, 2))


def _ripples(img, ramp, period: int):
    """Sand: wind ripples. The wave uses the FULL tile width, so its phase is
    continuous across the seam; `period` must divide the height for the same reason."""
    h, w = img.shape[:2]
    for x in range(w):
        off = int(round(1.5 * np.sin(2 * np.pi * x / w)))
        for y in range(0, h, period):
            _put(img, y + off, x, ramp.shadow)
            _put(img, y + off + 1, x, ramp.highlight)


def _drifts(img, ramp, r, n):
    """Snow: banked drifts, each a CLUSTER of offset lobes rather than one disc — a
    single disc reads as a polka dot, and against near-white snow any hard shadow
    scoop reads as a grey block, so the drift is built from highlight only and gets
    its shape from lumpiness instead of shading."""
    h, w = img.shape[:2]
    for _ in range(n):
        cy, cx = int(r.integers(0, h)), int(r.integers(0, w))
        for _ in range(3):
            _disc(img, cy + int(r.integers(-2, 3)), cx + int(r.integers(-3, 4)),
                  float(r.uniform(2.0, 3.0)), ramp.highlight)


def _crust(img, ramp, r, n):
    """Lava: dark crust plates floating on a glowing base, so the GAPS between them
    read as molten fissures — the inverse of drawing orange noise."""
    h, w = img.shape[:2]
    img[:] = (*ramp.highlight, 255)
    centres = [(int(r.integers(0, h)), int(r.integers(0, w))) for _ in range(n)]
    for cy, cx in centres:
        _disc(img, cy, cx, 4.2, ramp.shadow)
    for cy, cx in centres:
        _disc(img, cy, cx, 2.8, ramp.base)


def _wave(img, ramp, period: int):
    """Water: ripple courses. `period` must DIVIDE the tile height — the old step of
    3 into a 16px tile put courses at rows 0,3,..,15, so the last one landed 1px from
    the next tile's first and the water visibly banded at every seam."""
    h, w = img.shape[:2]
    for i, y in enumerate(range(0, h, period)):
        for x in range(w):
            crest = (x + i * 2) % 4 < 2
            _put(img, y, x, ramp.shadow if crest else ramp.base)
            _put(img, y + 1, x, ramp.highlight if crest else ramp.base)


def _brick(img, ramp):
    """Running-bond courses (already tileable: 4 and 8 both divide 16)."""
    h, w = img.shape[:2]
    for y in range(h):
        off = 0 if (y // 4) % 2 == 0 else 4        # every other course shifts a half-brick
        for x in range(w):
            if y % 4 == 0 or (x + off) % 8 == 0:
                _put(img, y, x, ramp.shadow)        # mortar joints
            elif y % 4 == 1:
                _put(img, y, x, ramp.highlight)     # lit top edge of each brick


def build_tile(contract, name: str, *, speckle: float = 0.22, wave: bool = False,
               cracks: int = 0, brick: bool = False, blades: int = 0,
               pebbles: int = 0, ripples: bool = False, drifts: int = 0,
               crust: bool = False) -> np.ndarray:
    w, h = contract.canvas_of("terrain_tile")
    ramp = Ramp(TILE_MATERIALS[name])
    r = _rng(name)
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[:] = (*ramp.base, 255)

    if crust:                                     # replaces the base fill; must come first
        _crust(img, ramp, r, 7)
    if speckle:                                   # texture grain (tileable, no bevel)
        noise = r.random((h, w))
        img[noise < speckle] = (*ramp.shadow, 255)
        img[noise > 1.0 - speckle * 0.55] = (*ramp.highlight, 255)
    if blades:
        _blades(img, ramp, r, blades)
    if pebbles:
        _pebbles(img, ramp, r, pebbles)
    if cracks:
        _cracks(img, ramp, r, int(cracks))
    if ripples:
        _ripples(img, ramp, RIPPLE_PERIOD)
    if drifts:
        _drifts(img, ramp, r, drifts)
    if wave:
        _wave(img, ramp, WAVE_PERIOD)
    if brick:
        _brick(img, ramp)
    return img


# The terrain-tile vocabulary: tile name -> build_tile kwargs. PUBLIC, because
# cross-reference validation in the spec store resolves level legends against it.
# It used to be read as ProceduralGenerator._TILES; a private attribute reached
# across a package boundary means a rename silently degrades that check to a no-op
# (the caller's `except Exception` swallows it). Use TILES / known_tiles() /
# tile_options() instead, so a rename is an AttributeError somebody has to fix.
TILES: dict[str, dict] = {
    "grass": dict(speckle=0.14, blades=18),
    "dirt": dict(speckle=0.13, pebbles=10),
    "water": dict(speckle=0.0, wave=True),
    "stone": dict(speckle=0.07, cracks=5),
    "sand": dict(speckle=0.09, ripples=True),
    "snow": dict(speckle=0.06, drifts=3),
    "lava": dict(speckle=0.0, crust=True),
    "brick": dict(speckle=0.0, brick=True),
}

TILE_DEFAULT = {"name": "grass"}


def known_tiles() -> list[str]:
    """Every terrain-tile name the generator can build, sorted."""
    return sorted(TILES)


def tile_options(name: str) -> dict:
    """The build_tile kwargs for one tile name ({} if unknown)."""
    return dict(TILES.get(name, {}))


class ProceduralGenerator(Generator):
    name = "procedural"

    _TILES = TILES                       # back-compat alias; prefer the module-level TILES

    def supports(self, spec: AssetSpec) -> bool:
        return spec.name in TILES

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        if spec.name not in TILES:
            raise NotImplementedError(
                f"procedural backend makes terrain tiles, not {spec.name!r}")
        return Image.fromarray(build_tile(contract, spec.name, **TILES[spec.name]), "RGBA")
