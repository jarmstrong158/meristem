"""Generator plugin boundary: `generate(spec, contract) -> PIL.Image`.

Every backend (procedural, agent-drawn, and any future paid-API or CC0-LoRA backend)
implements the same tiny interface, so the asset gate and everything downstream never
need to know which backend produced a pixel. Backends work in palette-index space
(0..N-1, -1 = transparent) and share the drawing helpers below.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

TRANSPARENT = -1


@dataclass
class AssetSpec:
    """What to draw — a projection of the manifest's entity/item/tile entry."""
    asset_class: str                 # matches a class in the style contract
    name: str                        # "grass", "player", "sword", ...
    variant: Optional[str] = None    # "idle", "walk", ...
    materials: list[str] = field(default_factory=list)  # palette color names
    facing: Optional[str] = None

    @property
    def stem(self) -> str:
        return self.name + (f"_{self.variant}" if self.variant else "")


class Generator(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, spec: AssetSpec, contract) -> Image.Image:
        """Return a native-size RGBA image conforming to the contract for spec.asset_class."""
        raise NotImplementedError

    def generate_frames(self, spec: AssetSpec, contract) -> list[Image.Image]:
        """Return the frames for an animated variant. Default: a single frame."""
        return [self.generate(spec, contract)]

    def supports(self, spec: AssetSpec) -> bool:
        return True


# --------------------------- index-grid drawing ----------------------------
def new_grid(w: int, h: int) -> np.ndarray:
    return np.full((h, w), TRANSPARENT, dtype=np.int16)


def render(grid: np.ndarray, palette_rgb: np.ndarray) -> Image.Image:
    h, w = grid.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    mask = grid >= 0
    idx = np.clip(grid, 0, len(palette_rgb) - 1)
    out[..., :3] = palette_rgb[idx]
    out[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def stable_rng(name: str) -> np.random.Generator:
    seed = int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)
    return np.random.default_rng(seed)


def disc(g: np.ndarray, cy, cx, ry, rx, color) -> None:
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    g[((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0] = color


def bevel(g: np.ndarray, light: int, shadow: int) -> None:
    """1px highlight on top/left silhouette edges, shadow on bottom/right."""
    h, w = g.shape
    op = g >= 0
    for y in range(h):
        for x in range(w):
            if not op[y, x]:
                continue
            up = (y == 0) or not op[y - 1, x]
            lf = (x == 0) or not op[y, x - 1]
            dn = (y == h - 1) or not op[y + 1, x]
            rt = (x == w - 1) or not op[y, x + 1]
            if up or lf:
                g[y, x] = light
            elif dn or rt:
                g[y, x] = shadow


def outline(g: np.ndarray, color: int) -> None:
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
                    add.append((y, x)); break
    for y, x in add:
        g[y, x] = color


_HEX = "0123456789abcdef"


def parse_block(rows: list[str]) -> np.ndarray:
    h = len(rows)
    w = max(len(r) for r in rows)
    g = new_grid(w, h)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "." or ch == " ":
                continue
            g[y, x] = _HEX.index(ch)
    return g


def place_block(block: np.ndarray, w: int, h: int, anchor: str) -> np.ndarray:
    g = new_grid(w, h)
    bh, bw = block.shape
    ox = (w - bw) // 2
    oy = h - bh - 1 if anchor == "bottom_center" else (h - bh) // 2
    for y in range(bh):
        for x in range(bw):
            if block[y, x] >= 0 and 0 <= oy + y < h and 0 <= ox + x < w:
                g[oy + y, ox + x] = block[y, x]
    return g
