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
    if not gen.supports(spec):                      # procedural makes tiles only (dec-0011/0021)
        pytest.skip(f"{backend} does not build {spec.asset_class}:{spec.name}")
    img = gen.generate(spec, contract)
    w, h = contract.canvas_of(spec.asset_class)
    assert img.size == (w, h)
    # generators emit final, gate-conformant art -> validate (non-mutating) must accept
    res = validate(img, spec.asset_class, contract)
    assert res.accepted, f"{backend}/{spec.name}: {res.reasons}"
    assert res.report["semi_transparent_px"] == 0
    if contract.is_free_palette(spec.asset_class):
        assert res.report["unique_colors"] <= contract.max_colors   # within the colour budget
    else:
        assert res.report["subset_of_palette"]                      # locked-palette assets


@pytest.mark.parametrize("spec", SPECS, ids=lambda s: f"{s.asset_class}:{s.name}")
def test_normalize_accepts_generated(spec, contract):
    # normalize (outline off, since generators already outline) must also accept
    img = get("agent-drawn").generate(spec, contract)
    res = normalize(img, spec.asset_class, contract, outline=False)
    assert res.accepted, res.reasons


@pytest.mark.parametrize("backend,spec", [
    ("procedural", AssetSpec("terrain_tile", "grass")),
    ("agent-drawn", AssetSpec("character", "player", "idle")),
])
def test_generation_is_deterministic(backend, spec, contract):
    gen = get(backend)

    def to_bytes(im):
        b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()

    assert to_bytes(gen.generate(spec, contract)) == to_bytes(gen.generate(spec, contract))


def test_procedural_rejects_unknown_recipe(contract):
    with pytest.raises(NotImplementedError):
        get("procedural").generate(AssetSpec("item_icon", "spaceship"), contract)


def test_walk_cycle_frames(contract):
    spec = AssetSpec("character", "player", "walk")
    frames = get("agent-drawn").generate_frames(spec, contract)
    assert len(frames) == 4                              # step-stand-step-stand
    w, h = contract.canvas_of("character")
    for f in frames:
        assert f.size == (w, h)
        assert validate(f, "character", contract).accepted   # each frame passes the gate
    import numpy as np
    arrs = [np.asarray(f) for f in frames]
    assert not np.array_equal(arrs[0], arrs[2])          # the two step frames differ (opposite feet)
    assert np.array_equal(arrs[1], arrs[3])              # both stand frames identical


def test_blob_archetype_is_parametric(contract):
    import numpy as np
    from meristem_generators.creatures import build_blob
    from PIL import Image
    green = build_blob(contract, {"color": (96, 200, 96)})
    king = build_blob(contract, {"color": (80, 150, 235), "size": "l", "eyes": 3})
    assert not np.array_equal(green, king)                      # config drives the sprite
    for arr in (green, king):
        res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
        assert res.accepted, res.reasons
        assert res.report["unique_colors"] <= contract.max_colors


def test_item_archetypes_are_parametric(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.items import weapon, consumable, pickup
    sword, staff = weapon(contract), weapon(contract, {"kind": "staff"})
    flask, bottle = consumable(contract), consumable(contract, {"shape": "bottle"})
    mana = consumable(contract, {"shape": "bottle", "liquid": (70, 120, 230)})
    gem = pickup(contract, {"shape": "gem", "color": (90, 200, 230)})
    assert not np.array_equal(sword, staff)                # weapon kind drives the sprite
    assert not np.array_equal(flask, bottle)               # potion shape varies
    assert not np.array_equal(bottle, mana)                # same shape, different liquid
    for arr in (sword, staff, flask, bottle, mana, gem):
        assert validate(Image.fromarray(arr, "RGBA"), "item_icon", contract).accepted


def test_all_archetypes_build_and_gate(contract):
    from PIL import Image
    from meristem_generators import archetype_class, build_archetype, known_archetypes
    assert len(known_archetypes()) >= 10
    for name in known_archetypes():
        cfg = {"name": "grass"} if name == "tile" else {}
        im = build_archetype(contract, name, cfg)
        assert validate(im, archetype_class(name), contract).accepted, name


def test_creature_archetypes_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_blob, build_ghost
    blob, ghost = build_blob(contract), build_ghost(contract)
    ghost_pink = build_ghost(contract, {"color": (240, 180, 190)})
    assert not np.array_equal(blob, ghost)                 # distinct creature archetypes
    assert not np.array_equal(ghost, ghost_pink)           # parametric colour
    for arr in (blob, ghost, ghost_pink):
        assert validate(Image.fromarray(arr, "RGBA"), "enemy", contract).accepted


def test_quadruped_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_quadruped
    builds = {b: build_quadruped(contract, {"build": b}) for b in ("dog", "wolf", "boar", "cat")}
    arrs = list(builds.values())
    for i in range(len(arrs)):                              # every build is distinct
        for j in range(i + 1, len(arrs)):
            assert not np.array_equal(arrs[i], arrs[j])
    for b, arr in builds.items():                          # and each still gates
        res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
        assert res.accepted, f"{b}: {res.reasons}"
        assert res.report["unique_colors"] <= contract.max_colors
    # an unknown build falls back to the dog skeleton rather than crashing
    assert np.array_equal(build_quadruped(contract, {"build": "griffon"}), builds["dog"])


def test_animated_archetypes_yield_distinct_gating_frames(contract):
    import numpy as np
    from meristem_generators import archetype_frames, archetype_class
    # each animated archetype yields >1 frame, all gate, frame 0 == its static build,
    # and not every frame is identical (there is real motion)
    from meristem_generators import build_archetype
    cases = [("blob", {}), ("ghost", {}), ("quadruped", {}), ("flyer", {}), ("pickup", {"shape": "coin"})]
    for name, cfg in cases:
        frames = archetype_frames(contract, name, cfg)
        assert frames and len(frames) >= 2, name
        for fr in frames:
            assert validate(fr, archetype_class(name), contract).accepted, name
        arrs = [np.asarray(f) for f in frames]
        assert np.array_equal(arrs[0], np.asarray(build_archetype(contract, name, cfg))), f"{name} frame0"
        assert any(not np.array_equal(arrs[0], a) for a in arrs[1:]), f"{name} has no motion"
    # a non-coin pickup opts out of animation
    assert archetype_frames(contract, "pickup", {"shape": "heart"}) is None


def test_flyer_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_flyer
    builds = {b: build_flyer(contract, {"build": b}) for b in ("bat", "bird", "moth")}
    arrs = list(builds.values())
    for i in range(len(arrs)):
        for j in range(i + 1, len(arrs)):
            assert not np.array_equal(arrs[i], arrs[j])         # each build is distinct
    for b, arr in builds.items():
        res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
        assert res.accepted, f"{b}: {res.reasons}"


def test_default_generate_frames_is_single(contract):
    # a tile has no animation; generate_frames returns one frame
    frames = get("procedural").generate_frames(AssetSpec("terrain_tile", "grass"), contract)
    assert len(frames) == 1
