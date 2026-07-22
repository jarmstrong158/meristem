"""Emit a verified LDtk 1.5.3 `.ldtk` file (godot-ldtk-importer 2.0.1 compatible).

Per the verified format research: emit a RESOLVED Tiles layer (explicit gridTiles the
compiler computes from the semantic grid) rather than auto-layer rules — deterministic
and robust for a generated pipeline — paired with an IntGrid layer carrying the
semantic values. Field names/structure verified against ldtk.io/json (v1.5.3)."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .level import SEMANTIC, TILE_ORDER

GRID = 16
TILESET_UID = 1
GROUND_LAYER_UID = 2
SEMANTIC_LAYER_UID = 3
LEVEL_UID = 10


def build_tileset_png(assets_dir: str | Path) -> tuple[Image.Image, dict[str, int]]:
    """Compose the terrain tile PNGs into a single-row tileset. Returns (image, name->col)."""
    assets_dir = Path(assets_dir)
    index = {name: i for i, name in enumerate(TILE_ORDER)}
    sheet = Image.new("RGBA", (GRID * len(TILE_ORDER), GRID), (0, 0, 0, 0))
    for name, col in index.items():
        tile = Image.open(assets_dir / f"tile_{name}.png").convert("RGBA")
        sheet.alpha_composite(tile, (col * GRID, 0))
    return sheet, index


def _uid(n: int) -> str:
    return f"{n:08d}-0000-0000-0000-000000000000"


def build_ldtk(grid: list[list[str]], tile_index: dict[str, int], *,
               tileset_rel: str = "tileset.png", tileset_cols: int | None = None) -> dict:
    h = len(grid)
    w = len(grid[0]) if h else 0
    cols = tileset_cols or len(TILE_ORDER)

    grid_tiles = []
    intgrid_csv = []
    for y in range(h):
        for x in range(w):
            name = grid[y][x]
            intgrid_csv.append(SEMANTIC.get(name, 0))
            if name in tile_index:
                idx = tile_index[name]                     # column in a single-row tileset
                grid_tiles.append({
                    "px": [x * GRID, y * GRID],
                    "src": [idx * GRID, 0],
                    "f": 0,
                    "t": idx,
                    "d": [y * w + x],
                    "a": 1,
                })

    def layer_instance(identifier, ltype, def_uid, **extra):
        base = {
            "__identifier": identifier, "__type": ltype,
            "__cWid": w, "__cHei": h, "__gridSize": GRID, "__opacity": 1,
            "__pxTotalOffsetX": 0, "__pxTotalOffsetY": 0,
            "iid": _uid(def_uid * 100), "levelId": LEVEL_UID, "layerDefUid": def_uid,
            "pxOffsetX": 0, "pxOffsetY": 0, "visible": True, "seed": 1234567,
            "intGridCsv": [], "gridTiles": [], "autoLayerTiles": [],
            "entityInstances": [], "optionalRules": [], "overrideTilesetUid": None,
        }
        base.update(extra)
        return base

    return {
        "jsonVersion": "1.5.3",
        "iid": _uid(1),
        "appBuildId": 1, "nextUid": 100,
        "defaultGridSize": GRID, "bgColor": "#40465B", "defaultLevelBgColor": "#696A79",
        "worldLayout": "Free", "externalLevels": False, "toc": [], "worlds": [],
        "defs": {
            "layers": [
                {"__type": "Tiles", "type": "Tiles", "identifier": "Ground",
                 "uid": GROUND_LAYER_UID, "gridSize": GRID, "displayOpacity": 1,
                 "tilesetDefUid": TILESET_UID, "intGridValues": [], "intGridValuesGroups": [],
                 "autoRuleGroups": [], "parallaxFactorX": 0, "parallaxFactorY": 0,
                 "parallaxScaling": True, "pxOffsetX": 0, "pxOffsetY": 0},
                {"__type": "IntGrid", "type": "IntGrid", "identifier": "Semantic",
                 "uid": SEMANTIC_LAYER_UID, "gridSize": GRID, "displayOpacity": 1,
                 "intGridValues": [
                     {"value": SEMANTIC[n], "identifier": n, "color": "#808080", "groupUid": 0, "tile": None}
                     for n in TILE_ORDER],
                 "intGridValuesGroups": [], "autoRuleGroups": [],
                 "parallaxFactorX": 0, "parallaxFactorY": 0, "parallaxScaling": True,
                 "pxOffsetX": 0, "pxOffsetY": 0},
            ],
            "entities": [], "tilesets": [
                {"uid": TILESET_UID, "identifier": "Tileset", "relPath": tileset_rel,
                 "pxWid": cols * GRID, "pxHei": GRID, "tileGridSize": GRID,
                 "spacing": 0, "padding": 0, "__cWid": cols, "__cHei": 1,
                 "tags": [], "enumTags": [], "customData": [], "savedSelections": []}
            ],
            "enums": [], "externalEnums": [], "levelFields": [],
        },
        "levels": [{
            "identifier": "Level_0", "iid": _uid(2), "uid": LEVEL_UID,
            "worldX": 0, "worldY": 0, "worldDepth": 0,
            "pxWid": w * GRID, "pxHei": h * GRID,
            "__bgColor": "#696A79", "bgColor": None, "bgPos": None, "bgRelPath": None,
            "useAutoIdentifier": False, "externalRelPath": None,
            "fieldInstances": [], "__neighbours": [],
            "layerInstances": [
                layer_instance("Ground", "Tiles", GROUND_LAYER_UID,
                               __tilesetDefUid=TILESET_UID, __tilesetRelPath=tileset_rel,
                               gridTiles=grid_tiles),
                layer_instance("Semantic", "IntGrid", SEMANTIC_LAYER_UID, intGridCsv=intgrid_csv),
            ],
        }],
    }


def write_ldtk(grid: list[list[str]], assets_dir: str | Path, levels_dir: str | Path,
               name: str = "grove_01") -> dict:
    levels_dir = Path(levels_dir)
    levels_dir.mkdir(parents=True, exist_ok=True)
    sheet, tile_index = build_tileset_png(assets_dir)
    sheet.save(levels_dir / "tileset.png")
    doc = build_ldtk(grid, tile_index)
    (levels_dir / f"{name}.ldtk").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    # runtime grid for the zero-addon ground builder
    (levels_dir / f"{name}.grid.json").write_text(
        json.dumps({"w": len(grid[0]), "h": len(grid), "grid": grid}), encoding="utf-8")
    return {"ldtk": f"{name}.ldtk", "tileset": "tileset.png", "grid_json": f"{name}.grid.json",
            "tiles": len([c for row in grid for c in row])}
