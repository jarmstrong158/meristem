"""Palette quantization strategies. All map opaque pixels onto the locked palette;
transparent pixels are left untouched (their RGB is irrelevant under hard alpha)."""
from __future__ import annotations

import numpy as np


def _nearest_indices(rgb: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """rgb: (...,3) int; returns (...) index of nearest palette color (sq. euclidean)."""
    flat = rgb.reshape(-1, 3).astype(np.int32)
    d = ((flat[:, None, :] - palette_rgb[None, :, :].astype(np.int32)) ** 2).sum(-1)  # (M,N)
    return d.argmin(1).reshape(rgb.shape[:-1])


def quantize_nearest(arr: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """arr: (H,W,4) uint8 RGBA. Snap opaque RGB to nearest palette color."""
    out = arr.copy()
    opaque = out[..., 3] == 255
    idx = _nearest_indices(out[..., :3], palette_rgb)
    snapped = palette_rgb[idx].astype(np.uint8)
    out[..., :3] = np.where(opaque[..., None], snapped, out[..., :3])
    return out


def quantize_nearest_dither(arr: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """Floyd–Steinberg error diffusion constrained to the locked palette.
    Only opaque pixels participate; error is not pushed into transparent pixels."""
    out = arr.copy()
    h, w, _ = out.shape
    work = out[..., :3].astype(np.float32)
    opaque = out[..., 3] == 255
    pal = palette_rgb.astype(np.float32)
    for y in range(h):
        for x in range(w):
            if not opaque[y, x]:
                continue
            old = work[y, x].copy()
            i = int(((old[None, :] - pal) ** 2).sum(-1).argmin())
            new = pal[i]
            work[y, x] = new
            err = old - new
            for dx, dy, f in ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and opaque[ny, nx]:
                    work[ny, nx] += err * f
    out[..., :3] = np.clip(work, 0, 255).astype(np.uint8)
    return out


STRATEGIES = {
    "nearest": quantize_nearest,
    "nearest_dither": quantize_nearest_dither,
}


def quantize(arr: np.ndarray, palette_rgb: np.ndarray, strategy: str = "nearest") -> np.ndarray:
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown quantize strategy {strategy!r}; known: {sorted(STRATEGIES)}")
    return STRATEGIES[strategy](arr, palette_rgb)
