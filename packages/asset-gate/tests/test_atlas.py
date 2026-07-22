import numpy as np
from PIL import Image

from asset_gate.atlas import AnimationTag, pack


def _solid(w, h, rgb):
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[..., :3] = rgb
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def test_empty_pack():
    at = pack([])
    assert at.frames == []
    assert at.manifest()["animations"] == []


def test_frames_within_bounds_and_no_overlap():
    entries = [("a", _solid(16, 16, (255, 0, 0))),
               ("b", _solid(16, 16, (0, 255, 0))),
               ("c", _solid(32, 32, (0, 0, 255)))]
    at = pack(entries, max_width=64, padding=1)
    W, H = at.image.size
    rects = [(f.x, f.y, f.w, f.h) for f in at.frames]
    for x, y, w, h in rects:
        assert x >= 0 and y >= 0 and x + w <= W and y + h <= H
    # pairwise non-overlap
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            ax, ay, aw, ah = rects[i]
            bx, by, bw, bh = rects[j]
            disjoint = (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)
            assert disjoint


def test_manifest_shape_and_stable_order():
    entries = [("first", _solid(8, 8, (255, 0, 0))),
               ("second", _solid(8, 8, (0, 255, 0)))]
    anim = AnimationTag(name="spin", frames=["first", "second"], fps=12, loop=True)
    at = pack(entries, animations=[anim])
    m = at.manifest()
    assert list(m["frames"].keys()) == ["first", "second"]  # input order preserved
    assert m["animations"][0]["name"] == "spin"
    assert m["animations"][0]["fps"] == 12
    for name in ("first", "second"):
        f = m["frames"][name]
        assert set(f) >= {"x", "y", "w", "h"}


def test_pixels_land_at_declared_slots():
    entries = [("red", _solid(16, 16, (255, 0, 0))),
               ("blue", _solid(16, 16, (0, 0, 255)))]
    at = pack(entries, max_width=64)
    arr = np.asarray(at.image)
    for f in at.frames:
        px = arr[f.y + 1, f.x + 1]
        expect = (255, 0, 0) if f.name == "red" else (0, 0, 255)
        assert tuple(px[:3]) == expect


def test_pivot_recorded():
    at = pack([("p", _solid(16, 16, (1, 2, 3)))], pivots={"p": (8, 15)})
    assert at.manifest()["frames"]["p"]["pivot"] == [8, 15]
