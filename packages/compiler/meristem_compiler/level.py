"""Synthesize a level grid for the vertical slice.

A real pipeline carries level layouts in the manifest; the slice's world domain only
names regions/levels, so the compiler synthesizes a small deterministic grove layout
(grass base + dirt path + water pond + stone cluster). One grid, projected into both
the .ldtk file (canonical, editable) and the runtime ground builder."""
from __future__ import annotations

# semantic IntGrid values (0 = empty is reserved)
SEMANTIC = {"grass": 1, "dirt": 2, "water": 3, "stone": 4}
# tileset column order -> tile index
TILE_ORDER = ["grass", "dirt", "water", "stone"]


def synthesize_grove(w: int = 20, h: int = 12) -> list[list[str]]:
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
