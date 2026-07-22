"""Individual, composable raster operations. All operate on (H,W,4) uint8 arrays
unless noted. No operation introduces a semi-transparent pixel."""
from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image


def to_rgba_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGBA")).copy()


def to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(arr, "RGBA")


def enforce_hard_alpha(arr: np.ndarray, threshold: int = 128) -> np.ndarray:
    out = arr.copy()
    a = out[..., 3]
    out[..., 3] = np.where(a >= threshold, 255, 0).astype(np.uint8)
    return out


def content_bbox(arr: np.ndarray) -> Optional[tuple[int, int, int, int]]:
    """(x0, y0, x1, y1) half-open of opaque content, or None if fully transparent."""
    opaque = arr[..., 3] == 255
    if not opaque.any():
        return None
    ys, xs = np.where(opaque)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def trim(arr: np.ndarray) -> tuple[np.ndarray, Optional[tuple[int, int, int, int]]]:
    box = content_bbox(arr)
    if box is None:
        return arr[:0, :0], None
    x0, y0, x1, y1 = box
    return arr[y0:y1, x0:x1].copy(), box


def place_on_canvas(content: np.ndarray, w: int, h: int, anchor: str) -> tuple[np.ndarray, tuple[int, int]]:
    """Place trimmed content on a transparent w×h canvas per anchor rule.
    Returns (canvas, (offset_x, offset_y))."""
    canvas = np.zeros((h, w, 4), dtype=np.uint8)
    ch, cw = content.shape[:2]
    if anchor == "top_left":
        ox, oy = 0, 0
    elif anchor == "bottom_center":
        ox, oy = (w - cw) // 2, h - ch
    else:  # center
        ox, oy = (w - cw) // 2, (h - ch) // 2
    ox, oy = max(0, ox), max(0, oy)
    canvas[oy:oy + ch, ox:ox + cw] = content
    return canvas, (ox, oy)


def apply_outline(arr: np.ndarray, color_rgb: tuple[int, int, int]) -> np.ndarray:
    """Add a 1px hard outline into transparent pixels 4-adjacent to opaque content."""
    out = arr.copy()
    opaque = out[..., 3] == 255
    nbr = np.zeros_like(opaque)
    nbr[1:, :] |= opaque[:-1, :]
    nbr[:-1, :] |= opaque[1:, :]
    nbr[:, 1:] |= opaque[:, :-1]
    nbr[:, :-1] |= opaque[:, 1:]
    edge = nbr & ~opaque
    out[edge, 0] = color_rgb[0]
    out[edge, 1] = color_rgb[1]
    out[edge, 2] = color_rgb[2]
    out[edge, 3] = 255
    return out


def fill_background(arr: np.ndarray, color_rgb: tuple[int, int, int]) -> np.ndarray:
    """Make every pixel opaque with transparent areas set to color_rgb (for tiles
    that must be fully opaque edge to edge)."""
    out = arr.copy()
    transparent = out[..., 3] != 255
    out[transparent, 0] = color_rgb[0]
    out[transparent, 1] = color_rgb[1]
    out[transparent, 2] = color_rgb[2]
    out[..., 3] = 255
    return out


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def darkest_opaque_color(arr: np.ndarray) -> Optional[tuple[int, int, int]]:
    opaque = arr[arr[..., 3] == 255][:, :3]
    if len(opaque) == 0:
        return None
    uniq = {tuple(int(c) for c in px) for px in opaque}
    return min(uniq, key=luminance)
