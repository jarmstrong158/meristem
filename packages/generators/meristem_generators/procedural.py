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


def _rng(name: str) -> np.random.Generator:
    seed = int(hashlib.sha256(("proc:" + name).encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


def build_tile(contract, name: str, *, speckle: float = 0.22, wave: bool = False,
               cracks: bool = False, brick: bool = False) -> np.ndarray:
    w, h = contract.canvas_of("terrain_tile")
    ramp = Ramp(TILE_MATERIALS[name])
    r = _rng(name)
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[:] = (*ramp.base, 255)

    def put(mask, rgb):
        img[mask] = (*rgb, 255)

    if speckle:                                   # texture grain (tileable, no bevel)
        noise = r.random((h, w))
        put(noise < speckle, ramp.shadow)
        put(noise > 1.0 - speckle * 0.55, ramp.highlight)
    if wave:                                       # water ripples
        for y in range(0, h, 3):
            xs = np.arange(w)
            put((slice(y, y + 1), (xs + y // 3) % 4 < 2), ramp.shadow)
            yy = (y + 1) % h
            put((slice(yy, yy + 1), (xs + y // 3) % 4 >= 2), ramp.highlight)
    if cracks:
        for _ in range(3):
            x, y = int(r.integers(2, w - 2)), int(r.integers(2, h - 2))
            for _ in range(int(r.integers(2, 5))):
                img[y, x] = (*ramp.shadow, 255)
                x = min(w - 1, max(0, x + int(r.integers(-1, 2))))
                y = min(h - 1, y + 1)
    if brick:                                      # running-bond courses (tileable)
        for y in range(h):
            band = y // 4
            off = 0 if band % 2 == 0 else 4        # every other course shifts a half-brick
            mortar_row = (y % 4 == 0)
            for x in range(w):
                if mortar_row or (x + off) % 8 == 0:
                    img[y, x] = (*ramp.shadow, 255)      # mortar joints
                elif y % 4 == 1:
                    img[y, x] = (*ramp.highlight, 255)   # lit top edge of each brick
    return img


class ProceduralGenerator(Generator):
    name = "procedural"

    _TILES = {
        "grass": dict(speckle=0.30),
        "dirt": dict(speckle=0.22, cracks=True),
        "water": dict(speckle=0.0, wave=True),
        "stone": dict(speckle=0.14, cracks=True),
        "sand": dict(speckle=0.16),
        "snow": dict(speckle=0.08),
        "lava": dict(speckle=0.10, wave=True),
        "brick": dict(speckle=0.0, brick=True),
    }

    def supports(self, spec: AssetSpec) -> bool:
        return spec.name in self._TILES

    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        if spec.name not in self._TILES:
            raise NotImplementedError(
                f"procedural backend makes terrain tiles, not {spec.name!r}")
        return Image.fromarray(build_tile(contract, spec.name, **self._TILES[spec.name]), "RGBA")
