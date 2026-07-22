"""Integration: every generated asset must pass the asset gate."""
import io
from pathlib import Path

import pytest

from asset_gate import load_contract, validate, normalize
from meristem_generators import AssetSpec, available, get

CONTRACT = Path(__file__).resolve().parents[3] / "experiments" / "00-bakeoff" / "style-contract.json"

SPECS = [
    AssetSpec("terrain_tile", "grass"), AssetSpec("terrain_tile", "dirt"),
    AssetSpec("terrain_tile", "water"), AssetSpec("terrain_tile", "stone"),
    AssetSpec("character", "player", "idle"), AssetSpec("enemy", "slime", "idle"),
    AssetSpec("item_icon", "sword"), AssetSpec("item_icon", "potion"),
    AssetSpec("item_icon", "key"), AssetSpec("ui_element", "heart"),
    AssetSpec("ui_element", "coin"),
]


@pytest.fixture(scope="module")
def contract():
    return load_contract(CONTRACT)


def test_registry_has_both_backends():
    assert "procedural" in available()
    assert "agent-drawn" in available()
    with pytest.raises(KeyError):
        get("nonexistent")


@pytest.mark.parametrize("backend", ["procedural", "agent-drawn"])
@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.asset_class}:{s.name}")
def test_generated_asset_passes_gate(backend, spec, contract):
    gen = get(backend)
    img = gen.generate(spec, contract)
    w, h = contract.canvas_of(spec.asset_class)
    assert img.size == (w, h)
    # generators emit final, gate-conformant art -> validate (non-mutating) must accept
    res = validate(img, spec.asset_class, contract)
    assert res.accepted, f"{backend}/{spec.name}: {res.reasons}"
    assert res.report["subset_of_palette"]
    assert res.report["semi_transparent_px"] == 0


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.asset_class}:{s.name}")
def test_normalize_accepts_generated(spec, contract):
    # normalize (outline off, since generators already outline) must also accept
    img = get("agent-drawn").generate(spec, contract)
    res = normalize(img, spec.asset_class, contract, outline=False)
    assert res.accepted, res.reasons


@pytest.mark.parametrize("backend", ["procedural", "agent-drawn"])
def test_generation_is_deterministic(backend, contract):
    gen = get(backend)
    spec = AssetSpec("character", "player", "idle")

    def to_bytes(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

    assert to_bytes(gen.generate(spec, contract)) == to_bytes(gen.generate(spec, contract))


def test_procedural_rejects_unknown_recipe(contract):
    with pytest.raises(NotImplementedError):
        get("procedural").generate(AssetSpec("item_icon", "spaceship"), contract)
