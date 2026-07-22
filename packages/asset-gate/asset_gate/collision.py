"""Derive a collision polygon from an asset's alpha channel.

Method: extract the boundary of the opaque region as unit grid edges, chain them
into closed loops, then Douglas-Peucker simplify. Returns polygon vertices in pixel
coordinates (x right, y down). Holes are ignored — the largest-area loop is the hull.
Deterministic; numpy-only."""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

import numpy as np
from PIL import Image

Point = tuple[float, float]


def _boundary_loops(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    h, w = mask.shape
    adj: dict[tuple[int, int], set] = defaultdict(set)

    def add(a, b):
        adj[a].add(b)
        adj[b].add(a)

    ys, xs = np.where(mask)
    for py, px in zip(ys.tolist(), xs.tolist()):
        if py == 0 or not mask[py - 1, px]:
            add((px, py), (px + 1, py))            # top
        if py == h - 1 or not mask[py + 1, px]:
            add((px, py + 1), (px + 1, py + 1))    # bottom
        if px == 0 or not mask[py, px - 1]:
            add((px, py), (px, py + 1))            # left
        if px == w - 1 or not mask[py, px + 1]:
            add((px + 1, py), (px + 1, py + 1))    # right

    used: set = set()
    loops: list[list[tuple[int, int]]] = []
    for start in list(adj):
        for first in sorted(adj[start]):
            edge = frozenset((start, first))
            if edge in used:
                continue
            loop = [start]
            used.add(edge)
            prev, cur = start, first
            while cur != start:
                loop.append(cur)
                nbrs = sorted(n for n in adj[cur] if frozenset((cur, n)) not in used)
                if not nbrs:
                    break
                nxt = nbrs[0]
                used.add(frozenset((cur, nxt)))
                prev, cur = cur, nxt
            if cur == start and len(loop) >= 4:
                loops.append(loop)
    return loops


def _perp_dist(p: Point, a: Point, b: Point) -> float:
    if a == b:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - proj[0], p[1] - proj[1])


def _dp(points: list[Point], tol: float) -> list[Point]:
    if len(points) < 3:
        return points
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > tol:
        left = _dp(points[:idx + 1], tol)
        right = _dp(points[idx:], tol)
        return left[:-1] + right
    return [points[0], points[-1]]


def _area(poly: list) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def alpha_to_polygons(image: Image.Image, tolerance: float = 1.0,
                      alpha_threshold: int = 255) -> list[list[Point]]:
    """All boundary loops, simplified, sorted by area descending."""
    mask = np.asarray(image.convert("RGBA"))[..., 3] >= alpha_threshold
    if not mask.any():
        return []
    polys = []
    for loop in _boundary_loops(mask):
        pts = [(float(x), float(y)) for x, y in loop]
        pts.append(pts[0])                 # close for DP
        simp = _dp(pts, tolerance)[:-1]    # drop the closing dup
        if len(simp) >= 3:
            polys.append(simp)
    polys.sort(key=_area, reverse=True)
    return polys


def alpha_to_polygon(image: Image.Image, tolerance: float = 1.0,
                     alpha_threshold: int = 255) -> list[Point]:
    """The single largest-area collision hull (empty list if fully transparent)."""
    polys = alpha_to_polygons(image, tolerance, alpha_threshold)
    return polys[0] if polys else []
