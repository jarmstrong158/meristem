import numpy as np

from asset_gate import palette as P


def test_nearest_snaps_offpalette(contract, make_rgba):
    pal = contract.palette_rgb
    arr = make_rgba(4, 4, fill=(254, 2, 80, 255))  # near red #FF004D
    out = P.quantize_nearest(arr, pal)
    # every opaque pixel is now exactly the red palette entry
    reds = {tuple(int(c) for c in px) for px in out[out[..., 3] == 255][:, :3]}
    assert reds == {(255, 0, 77)}


def test_transparent_pixels_untouched_in_alpha(contract, make_rgba):
    pal = contract.palette_rgb
    arr = make_rgba(4, 4, fill=(123, 45, 67, 0))  # transparent
    out = P.quantize_nearest(arr, pal)
    assert (out[..., 3] == 0).all()  # still transparent


def test_result_is_palette_subset(contract, make_rgba):
    pal = contract.palette_rgb
    rng = np.random.default_rng(0)
    arr = make_rgba(8, 8)
    arr[..., :3] = rng.integers(0, 256, size=(8, 8, 3))
    arr[..., 3] = 255
    out = P.quantize(arr, pal, "nearest")
    pal_set = {tuple(int(c) for c in row) for row in pal}
    got = {tuple(int(c) for c in px) for px in out[..., :3].reshape(-1, 3)}
    assert got.issubset(pal_set)


def test_dither_stays_in_palette(contract, make_rgba):
    pal = contract.palette_rgb
    arr = make_rgba(6, 6, fill=(128, 128, 128, 255))  # mid grey -> dithers to palette
    out = P.quantize(arr, pal, "nearest_dither")
    pal_set = {tuple(int(c) for c in row) for row in pal}
    got = {tuple(int(c) for c in px) for px in out[out[..., 3] == 255][:, :3]}
    assert got.issubset(pal_set)
