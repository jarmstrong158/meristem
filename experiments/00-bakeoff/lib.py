"""Shared bake-off library: palette, index-grid renderer, normalizer, metrics.

Both backends emit an *index grid* — a 2D array of palette indices (0..15) with
-1 meaning transparent. The single renderer turns that into an RGBA PNG. Because
the clean backends work in palette-index space, palette adherence and hard-alpha
are 100%/0 by construction; the normalizer/gate below still exists (and is what a
diffusion path would need), and the metrics measure it honestly.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / "style-contract.json").read_text(encoding="utf-8"))

TRANSPARENT = -1


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# palette index -> (r,g,b)
PALETTE: list[tuple[int, int, int]] = [_hex_to_rgb(c["hex"]) for c in CONTRACT["palette"]["colors"]]
PALETTE_RGB = np.array(PALETTE, dtype=np.int16)  # (16,3)
NAME_TO_I = {c["name"]: c["i"] for c in CONTRACT["palette"]["colors"]}
PAL_SET = {tuple(p) for p in PALETTE}


def canvas_of(cls: str) -> tuple[int, int]:
    c = CONTRACT["canvas"][cls]
    return c["w"], c["h"]


def outline_index_for(subject_indices: list[int]) -> int:
    """Contract rule: outline color = darkest shade of the subject's ramp.

    Approximate 'darkest' by luminance over the subject's own colors; fall back to
    the contract's fallback index (0 = black)."""
    if not subject_indices:
        return CONTRACT["outline"]["fallback_color_index"]
    def lum(i: int) -> float:
        r, g, b = PALETTE[i]
        return 0.299 * r + 0.587 * g + 0.114 * b
    return min(subject_indices, key=lum)


def new_grid(w: int, h: int) -> np.ndarray:
    return np.full((h, w), TRANSPARENT, dtype=np.int16)


def render(grid: np.ndarray) -> Image.Image:
    """index grid -> native-size RGBA image (hard alpha)."""
    h, w = grid.shape
    out = np.zeros((h, w, 4), dtype=np.uint8)
    mask = grid >= 0
    idx = np.clip(grid, 0, len(PALETTE) - 1)
    rgb = PALETTE_RGB[idx]  # (h,w,3)
    out[..., :3] = rgb
    out[..., 3] = np.where(mask, 255, 0).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def upscale(img: Image.Image, factor: int) -> Image.Image:
    return img.resize((img.width * factor, img.height * factor), Image.NEAREST)


def save_native_and_preview(grid: np.ndarray, path: Path, preview_factor: int = 8) -> None:
    img = render(grid)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    # preview at Nx for human/vision inspection, kept alongside
    prev = path.with_name(path.stem + f"@{preview_factor}x.png")
    upscale(img, preview_factor).save(prev)


# ---------------------------------------------------------------------------
# Normalizer / gate (what a non-palette source such as diffusion would need).
# For index-grid inputs this is a no-op; kept + measured for honesty.
# ---------------------------------------------------------------------------
def normalize_rgba(img: Image.Image) -> Image.Image:
    """Snap every pixel to the nearest palette color; enforce hard alpha."""
    arr = np.asarray(img.convert("RGBA")).astype(np.int16)
    rgb = arr[..., :3]
    a = arr[..., 3]
    # nearest palette color by squared euclidean distance
    d = ((rgb[:, :, None, :] - PALETTE_RGB[None, None, :, :]) ** 2).sum(-1)  # (h,w,16)
    nearest = d.argmin(-1)
    snapped = PALETTE_RGB[nearest].astype(np.uint8)
    hard_a = np.where(a >= 128, 255, 0).astype(np.uint8)
    out = np.dstack([snapped, hard_a])
    # transparent pixels carry palette rgb but alpha 0 (irrelevant)
    return Image.fromarray(out, "RGBA")


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def metric_palette_adherence(img: Image.Image) -> dict:
    arr = np.asarray(img.convert("RGBA"))
    opaque = arr[arr[..., 3] == 255][:, :3]
    if len(opaque) == 0:
        return {"opaque_px": 0, "exact_match_pct": 100.0, "unique_colors": 0, "subset_of_palette": True}
    tuples = {tuple(int(c) for c in px) for px in opaque}
    matches = sum(1 for px in opaque if tuple(int(c) for c in px) in PAL_SET)
    return {
        "opaque_px": int(len(opaque)),
        "exact_match_pct": round(100.0 * matches / len(opaque), 3),
        "unique_colors": len(tuples),
        "subset_of_palette": tuples.issubset(PAL_SET),
    }


def metric_alpha_discipline(img: Image.Image, cls: str) -> dict:
    a = np.asarray(img.convert("RGBA"))[..., 3]
    semi = int(((a > 0) & (a < 255)).sum())
    transparent = int((a == 0).sum())
    out = {"semi_transparent_px": semi}
    if cls == "terrain_tile":
        out["transparent_px_should_be_0"] = transparent
    return out


def metric_coverage(img: Image.Image) -> float:
    a = np.asarray(img.convert("RGBA"))[..., 3]
    return round(float((a == 255).mean()), 3)


def metric_seam(img: Image.Image) -> int:
    """Wrap-around seam discontinuity for a tileable base tile: count edge pixels
    whose opposite-edge neighbor differs. Lower = more seamlessly tileable."""
    arr = np.asarray(img.convert("RGBA"))[..., :3].astype(np.int16)
    top, bottom = arr[0, :, :], arr[-1, :, :]
    left, right = arr[:, 0, :], arr[:, -1, :]
    v = int((np.abs(top - bottom).sum(-1) > 24).sum())
    hh = int((np.abs(left - right).sum(-1) > 24).sum())
    return v + hh


def canvas_ok(img: Image.Image, cls: str) -> bool:
    w, h = canvas_of(cls)
    return img.width == w and img.height == h


def grid_hash(grid: np.ndarray) -> str:
    return hashlib.sha256(grid.tobytes()).hexdigest()[:16]


def assets() -> list[dict]:
    return CONTRACT["asset_set"]


def filename(a: dict) -> str:
    prefix = CONTRACT["naming"]["class_prefixes"][a["class"]]
    parts = [prefix, a["name"]]
    if a.get("variant"):
        parts.append(a["variant"])
    return "_".join(parts) + ".png"
