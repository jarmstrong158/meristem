"""Level grids: authored in the manifest's `levels` domain (legend + rows), with a
synthesized fallback for manifests that predate the domain.

One grid, projected into the .ldtk file (canonical, editable), the runtime ground
builder, and scene spawn placements."""
from __future__ import annotations

# semantic IntGrid values (0 = empty is reserved); stable across all known tiles
SEMANTIC = {"grass": 1, "dirt": 2, "water": 3, "stone": 4,
            "sand": 5, "snow": 6, "lava": 7, "brick": 8}
TILE_ORDER = ["grass", "dirt", "water", "stone", "sand", "snow", "lava", "brick"]


def grid_from_level(level: dict) -> list[list[str]]:
    """Expand an authored level (legend + rows) into a tile-name grid. The spec store's
    cross-ref validation guarantees rectangularity and legend coverage before compile."""
    legend = level["legend"]
    return [[legend[ch] for ch in row] for row in level["rows"]]


def pick_level(domains: dict) -> dict | None:
    """The level to compile: the first level of the first world region that defines
    one, else the first authored level, else None (fallback to the synthesized grove)."""
    levels = (domains.get("levels", {}) or {}).get("levels", [])
    if not levels:
        return None
    by_id = {lv["id"]: lv for lv in levels}
    for region in (domains.get("world", {}) or {}).get("regions", []):
        for lid in region.get("levels", []):
            if lid in by_id:
                return by_id[lid]
    return levels[0]


def synthesize_grove(w: int = 20, h: int = 12) -> list[list[str]]:
    """Fallback layout for manifests without a `levels` domain."""
    grid = [["grass" for _ in range(w)] for _ in range(h)]
    for x in range(w):                       # dirt path across the middle
        grid[6][x] = "dirt"
        grid[7][x] = "dirt"
    for y in range(2, 5):                    # water pond, top-right
        for x in range(13, 17):
            grid[y][x] = "water"
    for y in range(9, 11):                   # stone cluster, bottom-left
        for x in range(2, 5):
            grid[y][x] = "stone"
    return grid
