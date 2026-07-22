"""Hue-shifted shade derivation (ported from the Vanguard sprite style guide).

Classic pixel art never shades by pure brightness scaling. Shadows shift COOL
(hue toward blue/purple, slightly desaturated, darker); highlights shift WARM (hue
toward yellow, slightly more saturated, lighter). This is what lets a single base
color yield a believable 3-shade ramp — and why a locked arcade palette (which has
no such ramp for e.g. brown) can't do it.
"""
from __future__ import annotations

import colorsys

RGB = tuple[int, int, int]


def _to_hsv(rgb: RGB) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)


def _to_rgb(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def shadow(rgb: RGB, amount: float = 0.25) -> RGB:
    """Darker + cooler (hue toward blue ~0.65), slightly desaturated."""
    h, s, v = _to_hsv(rgb)
    h = _lerp(h, 0.65, amount * 0.3)
    s = min(1.0, s * (1.0 - amount * 0.15))
    v = max(0.0, v * (1.0 - amount))
    return _to_rgb(h, s, v)


def highlight(rgb: RGB, amount: float = 0.15) -> RGB:
    """Lighter + warmer (hue toward yellow ~0.13), slightly more saturated."""
    h, s, v = _to_hsv(rgb)
    h = _lerp(h, 0.13, amount * 0.4)
    s = min(1.0, s * (1.0 + amount * 0.1))
    v = min(1.0, v + amount)
    return _to_rgb(h, s, v)


class Ramp:
    """A material's 3-shade ramp derived from one base color."""
    __slots__ = ("shadow", "base", "highlight")

    def __init__(self, base: RGB, shadow_amt: float = 0.28, hi_amt: float = 0.16):
        self.base = base
        self.shadow = shadow(base, shadow_amt)
        self.highlight = highlight(base, hi_amt)
