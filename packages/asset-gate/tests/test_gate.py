import json

import numpy as np

from asset_gate import normalize, validate
from asset_gate.provenance import Provenance


def _solid(make_rgba, w, h, rgb, box=None):
    """A canvas with an opaque rgb rectangle (box=(x0,y0,x1,y1)) on transparency."""
    arr = make_rgba(w, h)
    if box is None:
        box = (0, 0, w, h)
    x0, y0, x1, y1 = box
    arr[y0:y1, x0:x1, :3] = rgb
    arr[y0:y1, x0:x1, 3] = 255
    return arr


# ------------------------------- sprites ----------------------------------
def test_accept_clean_icon(contract, make_rgba, to_img):
    # a small red blob well inside a 16x16 icon canvas
    arr = _solid(make_rgba, 20, 20, (255, 0, 77), box=(6, 6, 12, 12))
    res = normalize(to_img(arr), "item_icon", contract)
    assert res.accepted, res.reasons
    assert res.report["size"] == [16, 16]
    assert res.report["semi_transparent_px"] == 0
    assert res.report["subset_of_palette"]
    assert res.report["outline_applied"]
    assert res.image.size == (16, 16)


def test_reject_empty(contract, make_rgba, to_img):
    res = normalize(to_img(make_rgba(16, 16)), "item_icon", contract)
    assert not res.accepted
    assert any("empty" in r for r in res.reasons)
    assert res.image is None


def test_reject_oversize_content(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 40, 40, (0, 228, 54))  # fully opaque 40x40 > 16
    res = normalize(to_img(arr), "item_icon", contract)
    assert not res.accepted
    assert any("exceeds canvas" in r for r in res.reasons)


def test_offpalette_quantized_then_accepted(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 16, 16, (250, 5, 70), box=(5, 5, 10, 10))  # near-red
    res = normalize(to_img(arr), "item_icon", contract)
    assert res.accepted
    assert res.report["subset_of_palette"]


def test_semialpha_hardened_with_warning(contract, make_rgba, to_img):
    arr = make_rgba(16, 16)
    arr[4:10, 4:10, :3] = (41, 173, 255)  # blue
    arr[4:10, 4:10, 3] = 200              # semi-transparent, above threshold -> hardens opaque
    res = normalize(to_img(arr), "item_icon", contract)
    assert res.accepted, res.reasons
    assert res.report["semi_transparent_px"] == 0
    assert any("semi-transparent" in w for w in res.warnings)


def test_no_outline_flag(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 16, 16, (255, 0, 77), box=(6, 6, 10, 10))
    with_o = normalize(to_img(arr), "item_icon", contract, outline=True)
    without = normalize(to_img(arr), "item_icon", contract, outline=False)
    assert with_o.report["opaque_px"] > without.report["opaque_px"]


# -------------------------------- tiles -----------------------------------
def test_tile_accepts_full_bleed(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 16, 16, (0, 228, 54))  # fully opaque, exact size
    res = normalize(to_img(arr), "terrain_tile", contract)
    assert res.accepted, res.reasons
    assert res.report["transparent_px"] == 0


def test_tile_rejects_transparency(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 16, 16, (0, 228, 54))
    arr[0, 0, 3] = 0  # a hole
    res = normalize(to_img(arr), "terrain_tile", contract)
    assert not res.accepted
    assert any("fully opaque" in r for r in res.reasons)


def test_tile_rejects_wrong_size(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 10, 10, (0, 228, 54))
    res = normalize(to_img(arr), "terrain_tile", contract)
    assert not res.accepted
    assert any("!= canvas" in r for r in res.reasons)


# ----------------------------- provenance ---------------------------------
def test_provenance_populated_and_sidecar(contract, make_rgba, to_img, tmp_path):
    arr = _solid(make_rgba, 16, 16, (255, 236, 39), box=(5, 5, 11, 11))
    prov = Provenance(backend="agent-drawn", seed=7, created_at="2026-07-22T00:00:00+00:00")
    res = normalize(to_img(arr), "item_icon", contract, provenance=prov)
    assert res.accepted
    assert res.provenance.backend == "agent-drawn"
    assert res.provenance.contract_hash == contract.hash()
    assert res.provenance.gate_version
    out = tmp_path / "icon_coin.png"
    res.image.save(out)
    sidecar = res.provenance.write_sidecar(out)
    data = json.loads(sidecar.read_text())
    assert data["backend"] == "agent-drawn"
    assert data["seed"] == 7
    assert data["created_at"] == "2026-07-22T00:00:00+00:00"


# --------------------------- free palette ---------------------------------
def test_free_palette_accepts_offpalette_within_budget(contract, make_rgba, to_img):
    # 'character' is a free-palette class -> off-locked-palette colours OK if within budget
    arr = make_rgba(32, 32)
    arr[10:20, 10:22, :3] = (123, 45, 200)      # not in the locked fixture palette
    arr[10:20, 10:22, 3] = 255
    res = validate(to_img(arr), "character", contract)
    assert res.accepted, res.reasons
    assert not res.report["subset_of_palette"]  # genuinely off the locked palette


def test_free_palette_rejects_over_budget(contract, make_rgba, to_img):
    arr = make_rgba(32, 32)
    rng = np.random.default_rng(0)
    arr[0:20, 0:20, :3] = rng.integers(0, 256, size=(20, 20, 3))   # far more than 15 colours
    arr[0:20, 0:20, 3] = 255
    res = validate(to_img(arr), "character", contract)
    assert not res.accepted
    assert any("budget" in r for r in res.reasons)


def test_locked_class_still_rejects_offpalette(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 16, 16, (123, 45, 200))   # off-palette tile
    res = validate(to_img(arr), "terrain_tile", contract)
    assert not res.accepted
    assert any("locked palette" in r for r in res.reasons)


# ------------------------------ validate ----------------------------------
def test_validate_roundtrip(contract, make_rgba, to_img):
    arr = _solid(make_rgba, 20, 20, (255, 0, 77), box=(6, 6, 12, 12))
    norm = normalize(to_img(arr), "item_icon", contract)
    assert norm.accepted
    v = validate(norm.image, "item_icon", contract)
    assert v.accepted, v.reasons
