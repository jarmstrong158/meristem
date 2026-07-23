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
    if not contract.is_free_palette(spec.asset_class):
        assert res.report["subset_of_palette"]                      # locked-palette assets only


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
    # an unknown build falls back to the dog skeleton rather than crashing
    assert np.array_equal(build_quadruped(contract, {"build": "griffon"}), builds["dog"])


def test_animated_archetypes_yield_distinct_gating_frames(contract):
    import numpy as np
    from meristem_generators import archetype_frames, archetype_class
    # each animated archetype yields >1 frame, all gate, frame 0 == its static build,
    # and not every frame is identical (there is real motion)
    from meristem_generators import build_archetype
    cases = [("blob", {}), ("ghost", {}), ("quadruped", {}), ("flyer", {}),
             ("serpent", {}), ("spider", {}), ("pickup", {"shape": "coin"})]
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


def test_serpent_and_spider_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_serpent, build_spider
    for fn, builds in ((build_serpent, ("cobra", "snake", "viper")),
                       (build_spider, ("spider", "tarantula", "widow"))):
        arrs = {b: fn(contract, {"build": b}) for b in builds}
        vals = list(arrs.values())
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                assert not np.array_equal(vals[i], vals[j])     # each build distinct
        for b, arr in arrs.items():
            res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
            assert res.accepted, f"{fn.__name__} {b}: {res.reasons}"


def test_hair_styles_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.humanoid import build_humanoid
    styles = ["short", "long", "ponytail", "spiky", "bald"]
    arrs = {s: build_humanoid(contract, {"hair_style": s}) for s in styles}
    vals = list(arrs.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert not np.array_equal(vals[i], vals[j])         # each style distinct
    for s, a in arrs.items():
        assert validate(Image.fromarray(a, "RGBA"), "character", contract).accepted, s


def test_chest_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.items import chest
    arrs = {b: chest(contract, {"build": b}) for b in ("wood", "iron", "gold", "crystal")}
    vals = list(arrs.values())
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            assert not np.array_equal(vals[i], vals[j])         # each material distinct
    for b, a in arrs.items():
        assert validate(Image.fromarray(a, "RGBA"), "item_icon", contract).accepted, b


def test_new_tiles_build_and_gate(contract):
    from PIL import Image
    from meristem_generators.procedural import build_tile, ProceduralGenerator
    for name in ("sand", "snow", "lava", "brick"):
        arr = build_tile(contract, name, **ProceduralGenerator._TILES[name])
        res = validate(Image.fromarray(arr, "RGBA"), "terrain_tile", contract)
        assert res.accepted, f"{name}: {res.reasons}"


def test_item_kind_variety_builds_and_gates(contract):
    from PIL import Image
    from meristem_generators.items import weapon, consumable, projectile
    groups = [
        (weapon, "kind", ["sword", "dagger", "greatsword", "axe", "spear", "staff", "bow", "mace", "wand"]),
        (consumable, "shape", ["flask", "bottle", "vial", "scroll", "pouch"]),
        (projectile, "kind", ["arrow", "fireball", "bolt", "knife", "shuriken"]),
    ]
    for fn, key, kinds in groups:
        seen = set()
        for k in kinds:
            arr = fn(contract, {key: k})
            assert validate(Image.fromarray(arr, "RGBA"), "item_icon", contract).accepted, k
            seen.add(arr.tobytes())
        assert len(seen) == len(kinds), f"{fn.__name__}: some kinds render identically"


def test_humanoid_hat_beard_layers(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.humanoid import build_humanoid
    # classic archetypes from the one layered base; each must build + gate
    combos = [
        {},
        {"hat": "helmet", "hat_color": (176, 182, 194)},
        {"hat": "wizard", "hat_color": (70, 60, 140), "beard": "full", "hair": (220, 220, 225)},
        {"hat": "crown", "hat_color": (242, 214, 120), "beard": "full"},
        {"beard": "full", "hair": (170, 90, 50)},
        {"hat": "cap", "hat_color": (90, 70, 60), "hair_style": "ponytail"},
        {"beard": "short", "hair_style": "bald"},
    ]
    seen = set()
    for cfg in combos:
        a = build_humanoid(contract, cfg)
        r = validate(Image.fromarray(a, "RGBA"), "character", contract)
        assert r.accepted, (cfg, r.reasons)
        seen.add(a.tobytes())
    assert len(seen) == len(combos)                     # each archetype distinct


def test_pickup_variety(contract):
    from PIL import Image
    from meristem_generators.items import pickup
    for shape in ("coin", "heart", "key", "gem", "ring", "skull", "star"):
        cls = "ui_element" if shape in ("coin", "heart") else "item_icon"
        a = pickup(contract, {"shape": shape})
        assert validate(Image.fromarray(a, "RGBA"), cls, contract).accepted, shape


def test_raptor_and_beetle_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_raptor, build_beetle
    for fn, builds in ((build_raptor, ("raptor", "drake", "roc")),
                       (build_beetle, ("beetle", "scorpion", "mite"))):
        arrs = {b: fn(contract, {"build": b}) for b in builds}
        vals = list(arrs.values())
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                assert not np.array_equal(vals[i], vals[j])     # each build distinct
        for b, arr in arrs.items():
            res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
            assert res.accepted, f"{fn.__name__} {b}: {res.reasons}"


def test_blob_and_ghost_builds_vary(contract):
    import numpy as np
    from PIL import Image
    from meristem_generators.creatures import build_blob, build_ghost
    for fn, builds in ((build_blob, ("slime", "king", "cube", "ooze")),
                       (build_ghost, ("ghost", "wisp", "specter"))):
        arrs = {b: fn(contract, {"build": b}) for b in builds}
        vals = list(arrs.values())
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                assert not np.array_equal(vals[i], vals[j])     # each build distinct
        for b, arr in arrs.items():
            res = validate(Image.fromarray(arr, "RGBA"), "enemy", contract)
            assert res.accepted, f"{fn.__name__} {b}: {res.reasons}"


def test_contact_sheet_covers_the_library():
    # the library reference tool must keep building every archetype/build it lists
    import sys
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "tools"))
    import contact_sheet
    sections = contact_sheet.build_sections()
    total = sum(len(e) for _, e in sections)
    assert total >= 60, total
    for _, entries in sections:
        for label, sprite in entries:
            assert sprite.mode == "RGBA" and sprite.width in (16, 32), label


def test_sprite_catalog_covers_registry_and_builds_are_real():
    from meristem_generators import sprite_catalog, known_archetypes, build_archetype
    cat = {e["archetype"]: e for e in sprite_catalog()}
    assert set(cat) == set(known_archetypes())          # catalog == registry, no drift
    contract = load_contract(CONTRACT)
    for name, entry in cat.items():
        assert entry["class"] and isinstance(entry["variants"], dict)
        # every advertised build/kind/shape option must actually build + gate
        for key, options in entry["variants"].items():
            for opt in options:
                cfg = {key: opt}
                im = build_archetype(contract, name, cfg)
                from asset_gate import validate
                assert validate(im, entry["class"], contract).accepted, (name, key, opt)


def test_validate_sprite_catches_bogus_variant():
    from meristem_generators import validate_sprite
    assert validate_sprite("flyer", {"build": "bat"}) == []          # real build -> ok
    assert validate_sprite("flyer", {"build": "dragon"})             # typo -> problem
    assert validate_sprite("weapon", {"kind": "sword"}) == []
    assert validate_sprite("weapon", {"kind": "railgun"})
    assert validate_sprite("nonexistent", {})                        # unknown archetype
    assert validate_sprite("blob", {}) == []                         # no variant given -> ok (defaults)


def test_default_generate_frames_is_single(contract):
    # a tile has no animation; generate_frames returns one frame
    frames = get("procedural").generate_frames(AssetSpec("terrain_tile", "grass"), contract)
    assert len(frames) == 1
