"""Run a backend over the 11-asset set: generate, save, measure, compose.

Usage:  python run.py procedural
        python run.py agent_drawn
Outputs native PNGs + @8x previews, a metrics JSON, a labeled + blind contact
sheet, and a mock game scene composed from the assets.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import lib

HERE = Path(__file__).resolve().parent
STEMS = [
    "tile_grass", "tile_dirt", "tile_water", "tile_stone",
    "char_player_idle", "enemy_slime_idle",
    "icon_sword", "icon_potion", "icon_key",
    "ui_heart", "ui_coin",
]
CLASS_OF = {
    "tile_grass": "terrain_tile", "tile_dirt": "terrain_tile", "tile_water": "terrain_tile",
    "tile_stone": "terrain_tile", "char_player_idle": "character", "enemy_slime_idle": "enemy",
    "icon_sword": "item_icon", "icon_potion": "item_icon", "icon_key": "item_icon",
    "ui_heart": "ui_element", "ui_coin": "ui_element",
}
BG = (34, 32, 52, 255)  # neutral dark slate for sheets (NOT a palette color, on purpose)


def run(backend: str) -> dict:
    mod = importlib.import_module(f"gen_{backend}")
    outdir = HERE / backend.replace("_", "-")
    outdir.mkdir(parents=True, exist_ok=True)

    grids: dict[str, np.ndarray] = {}
    metrics = {}
    for stem in STEMS:
        g = mod.build(stem)
        grids[stem] = g
        cls = CLASS_OF[stem]
        lib.save_native_and_preview(g, outdir / f"{stem}.png")
        img = lib.render(g)
        m = {
            "class": cls,
            "canvas_ok": lib.canvas_ok(img, cls),
            "palette": lib.metric_palette_adherence(img),
            "alpha": lib.metric_alpha_discipline(img, cls),
            "coverage": lib.metric_coverage(img),
            "grid_hash": lib.grid_hash(g),
        }
        if cls == "terrain_tile":
            m["seam"] = lib.metric_seam(img)
        metrics[stem] = m

    (outdir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    _contact_sheet(grids, outdir, backend, labeled=True)
    _contact_sheet(grids, outdir, backend, labeled=False)
    _mock_scene(grids, outdir, backend)
    return metrics


def _contact_sheet(grids, outdir, backend, labeled: bool):
    scale = 8
    pad = 12
    cols = 4
    cellw = 32 * scale + pad
    cellh = 32 * scale + pad + (16 if labeled else 0)
    rows = (len(STEMS) + cols - 1) // cols
    W = cols * cellw + pad
    H = rows * cellh + pad + (28 if labeled else 0)
    sheet = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(sheet)
    if labeled:
        draw.text((pad, 6), f"{backend}  —  11-asset contact sheet", fill=(255, 241, 232, 255))
    for i, stem in enumerate(STEMS):
        r, c = divmod(i, cols)
        x = pad + c * cellw
        y = (28 if labeled else pad) + r * cellh
        cell = lib.upscale(lib.render(grids[stem]), scale)
        # center within a 32*scale box
        bw, bh = 32 * scale, 32 * scale
        ox = x + (bw - cell.width) // 2
        oy = y + (bh - cell.height) // 2
        sheet.alpha_composite(cell, (ox, oy))
        if labeled:
            draw.text((x, y + bh + 2), stem, fill=(194, 195, 199, 255))
    name = "contact_labeled.png" if labeled else "contact_blind.png"
    (HERE / "contact-sheets").mkdir(exist_ok=True)
    sheet.save(HERE / "contact-sheets" / f"{backend}_{name}")


def _mock_scene(grids, outdir, backend):
    """Compose a tiny game scene: ground of tiles, water patch, stone ledge, the
    player + slime standing on the ground, an item on the ground, HUD hearts+coin."""
    TW = 16
    cols_, rows_ = 20, 12  # 320x192
    scene = Image.new("RGBA", (cols_ * TW, rows_ * TW), (0, 0, 0, 255))

    def blit_tile(stem, cx, cy):
        scene.alpha_composite(lib.render(grids[stem]), (cx * TW, cy * TW))

    # sky = black; ground from row 9 down
    for x in range(cols_):
        blit_tile("tile_grass", x, 9)
        for y in range(10, rows_):
            blit_tile("tile_dirt", x, y)
    # water pond
    for x in range(13, 18):
        blit_tile("tile_water", x, 9)
    # stone ledge
    for x in range(2, 6):
        blit_tile("tile_stone", x, 7)

    def blit_sprite(stem, px, py_bottom):
        img = lib.render(grids[stem])
        # bottom_center anchor
        scene.alpha_composite(img, (px - img.width // 2, py_bottom - img.height))

    blit_sprite("char_player_idle", 5 * TW, 9 * TW)       # on stone ledge? place on ground
    blit_sprite("char_player_idle", 4 * TW, 7 * TW)       # standing on ledge
    blit_sprite("enemy_slime_idle", 10 * TW, 9 * TW)      # on grass
    # item on ground
    scene.alpha_composite(lib.render(grids["icon_sword"]), (8 * TW, 9 * TW - 16))
    # HUD: hearts + coin top-left
    for i in range(3):
        scene.alpha_composite(lib.render(grids["ui_heart"]), (2 + i * 16, 2))
    scene.alpha_composite(lib.render(grids["ui_coin"]), (2, 20))

    scene.save(outdir / "mock_scene.png")
    lib.upscale(scene, 3).save(HERE / "contact-sheets" / f"{backend}_mock_scene@3x.png")


if __name__ == "__main__":
    backend = sys.argv[1] if len(sys.argv) > 1 else "procedural"
    m = run(backend)
    ok = all(v["palette"]["exact_match_pct"] == 100.0 for v in m.values())
    print(f"[{backend}] {len(m)} assets. palette 100% on all: {ok}")
    for stem, v in m.items():
        extra = f" seam={v.get('seam')}" if "seam" in v else ""
        print(f"  {stem:20s} cov={v['coverage']:.2f} uniq={v['palette']['unique_colors']}"
              f" canvas_ok={v['canvas_ok']}{extra}")
