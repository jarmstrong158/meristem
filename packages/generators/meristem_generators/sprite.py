"""The shared sprite-construction standard.

Every generated sprite is built the same way (dec-0021): from named **materials**,
each of which auto-derives a 3-shade hue-shifted ramp (shadow cool / base / highlight
warm) via shading.Ramp; one light direction (top-left); a selective dark outline; a
colour budget. This is what makes independently-built assets read as one game — the
shared construction rules, not a single locked palette.
"""
from __future__ import annotations

import numpy as np

from .shading import Ramp, shadow

RGB = tuple[int, int, int]
_CLEAR = (0, 0, 0, 0)


class Canvas:
    """A tiny RGBA drawing surface. Every draw op takes a concrete RGB (a ramp shade)."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.img = np.zeros((h, w, 4), dtype=np.uint8)

    def px(self, r: int, c: int, rgb: RGB) -> None:
        if 0 <= r < self.h and 0 <= c < self.w:
            self.img[r, c] = (rgb[0], rgb[1], rgb[2], 255)

    def rect(self, r0: int, r1: int, c0: int, c1: int, rgb: RGB) -> None:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                self.px(r, c, rgb)

    def disc(self, cy: float, cx: float, ry: float, rx: float, rgb: RGB) -> None:
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        m = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
        self.img[m] = (rgb[0], rgb[1], rgb[2], 255)

    def clear_disc(self, cy: float, cx: float, ry: float, rx: float) -> None:
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        m = ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
        self.img[m] = _CLEAR

    def outline(self, rgb: RGB) -> None:
        """1px selective outline into transparent pixels 4-adjacent to opaque content."""
        op = self.img[..., 3] == 255
        nbr = np.zeros_like(op)
        nbr[1:, :] |= op[:-1, :]; nbr[:-1, :] |= op[1:, :]
        nbr[:, 1:] |= op[:, :-1]; nbr[:, :-1] |= op[:, 1:]
        edge = nbr & ~op
        self.img[edge] = (rgb[0], rgb[1], rgb[2], 255)

    def array(self) -> np.ndarray:
        return self.img


def outline_dark(base: RGB) -> RGB:
    """A near-black outline hued to a material (sel-out), not pure black."""
    return shadow(base, 0.66)


# ---- palette-safe transforms for animation frames (no new colours, no alpha) ----
def translate(arr: np.ndarray, dx: int = 0, dy: int = 0) -> np.ndarray:
    """Rigid pixel shift with transparent fill (no wrap) — for float/bob frames."""
    out = np.zeros_like(arr)
    h, w = arr.shape[:2]
    sr0, sr1 = max(0, -dy), min(h, h - dy)
    sc0, sc1 = max(0, -dx), min(w, w - dx)
    out[sr0 + dy:sr1 + dy, sc0 + dx:sc1 + dx] = arr[sr0:sr1, sc0:sc1]
    return out


def squeeze_h(arr: np.ndarray, factor: float) -> np.ndarray:
    """Scale content horizontally about the centre with NEAREST (colour- and
    alpha-exact, so the gate still passes). factor 1.0 = unchanged; <1 = narrower,
    e.g. a coin turning toward edge-on."""
    from PIL import Image
    im = Image.fromarray(arr, "RGBA")
    w, h = im.size
    nw = max(2, int(round(w * factor)))
    small = im.resize((nw, h), Image.NEAREST)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(small, ((w - nw) // 2, 0))
    return np.asarray(out)
