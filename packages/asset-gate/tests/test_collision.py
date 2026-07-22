import numpy as np
from PIL import Image

from asset_gate.collision import alpha_to_polygon, alpha_to_polygons


def _img(mask: np.ndarray) -> Image.Image:
    h, w = mask.shape
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[mask, :3] = 255
    arr[mask, 3] = 255
    return Image.fromarray(arr, "RGBA")


def test_empty_returns_no_polygon():
    assert alpha_to_polygon(_img(np.zeros((8, 8), bool))) == []
    assert alpha_to_polygons(_img(np.zeros((8, 8), bool))) == []


def test_filled_square_is_four_corners():
    m = np.zeros((10, 10), bool)
    m[2:8, 2:8] = True
    poly = alpha_to_polygon(_img(m), tolerance=1.0)
    assert len(poly) == 4
    xs = sorted({p[0] for p in poly})
    ys = sorted({p[1] for p in poly})
    assert xs == [2.0, 8.0]  # grid-corner coords bound the 6px-wide block
    assert ys == [2.0, 8.0]


def test_polygon_bounds_contain_content():
    m = np.zeros((16, 16), bool)
    m[3:12, 5:10] = True
    poly = alpha_to_polygon(_img(m))
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert min(xs) == 5.0 and max(xs) == 10.0
    assert min(ys) == 3.0 and max(ys) == 12.0


def test_tolerance_reduces_vertices_on_diagonal():
    # a filled triangle -> staircase hypotenuse; higher tolerance -> fewer vertices
    m = np.zeros((16, 16), bool)
    for y in range(12):
        m[y, 0:y + 1] = True
    fine = alpha_to_polygon(_img(m), tolerance=0.5)
    coarse = alpha_to_polygon(_img(m), tolerance=3.0)
    assert len(coarse) <= len(fine)
    assert len(coarse) >= 3


def test_largest_loop_selected_with_hole():
    # a ring (outer 12x12 minus inner 4x4) -> largest loop is the outer boundary
    m = np.zeros((16, 16), bool)
    m[2:14, 2:14] = True
    m[6:10, 6:10] = False
    polys = alpha_to_polygons(_img(m), tolerance=1.0)
    assert len(polys) >= 2  # outer + hole
    outer = polys[0]
    xs = [p[0] for p in outer]
    assert min(xs) == 2.0 and max(xs) == 14.0
