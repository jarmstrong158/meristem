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
    from meristem_generators.procedural import build_tile, known_tiles, tile_options
    assert {"sand", "snow", "lava", "brick"} <= set(known_tiles())
    for name in ("sand", "snow", "lava", "brick"):
        arr = build_tile(contract, name, **tile_options(name))
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


def test_color_keys_advertise_every_colour_knob_a_builder_actually_reads(contract):
    """The colour vocabulary must not drift from the builders.

    `_COLOR_KEYS` used to be a hand-maintained table and it rotted: `raptor` and
    `beetle` were added to the registry, both builders read cfg["color"], and neither
    was ever added to the table — so `list_sprite_archetypes` told authors those two
    archetypes had no colour knob at all. This test is behavioural, not declarative:
    it overrides each candidate knob and checks the RENDER changes. Any key that
    changes pixels is a real colour knob and MUST be advertised.
    """
    import numpy as np
    from meristem_generators import (archetype_defaults, build_archetype, color_keys,
                                     known_archetypes)

    loud = (255, 0, 255)                        # nothing defaults to magenta
    for name in known_archetypes():
        defaults = archetype_defaults(name)
        base = np.asarray(build_archetype(contract, name, {}))
        effective = set()
        for key, value in defaults.items():
            if not (isinstance(value, (tuple, list)) and len(value) in (3, 4)
                    and all(isinstance(c, int) and not isinstance(c, bool) for c in value)):
                continue                        # not a colour-shaped default
            if np.array_equal(np.asarray(build_archetype(contract, name, {key: loud})), base):
                continue                        # inert for the default variant (e.g. hat=none)
            effective.add(key)
        assert effective <= set(color_keys(name)), (
            f"{name}: colour knob(s) {sorted(effective - set(color_keys(name)))} change the "
            f"sprite but are not advertised in color_keys()")


def test_color_keys_regression_raptor_and_beetle(contract):
    """The exact drift that shipped: both read cfg["color"] but advertised nothing."""
    from meristem_generators import color_keys, sprite_catalog
    catalog = {e["archetype"]: e for e in sprite_catalog()}
    for name in ("raptor", "beetle"):
        assert "color" in color_keys(name), name
        assert "color" in catalog[name]["color_keys"], name   # and it reaches the MCP surface


def test_advertised_color_keys_build_and_gate(contract):
    """Every advertised knob must be accepted by the builder and still gate."""
    from meristem_generators import archetype_class, build_archetype, sprite_catalog
    for entry in sprite_catalog():
        name = entry["archetype"]
        for key in entry["color_keys"]:
            im = build_archetype(contract, name, {key: (120, 90, 200)})
            assert validate(im, archetype_class(name), contract).accepted, (name, key)


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


# --------------------------------------------------------------------------------
# Readability regressions.
#
# The "...builds_vary" tests above only assert that two renders are not byte-equal,
# which a one-pixel ear tweak satisfies. The library shipped a long time in a state
# where every one of them passed and the sprites were still indistinguishable on
# screen: dog/wolf/boar/cat were a single hardcoded body loaf differing by +/-1px of
# ear and leg. The tests below assert on what a player actually reads — SILHOUETTE
# and COLOUR — and each threshold is calibrated so it FAILS against the versions
# that shipped (measured: quadruped worst pair 46px, flyer 60px, blade widths
# 8/10/12) and passes with headroom now (144px, 108px, 6/12/16).
#
# Deliberately absent: an image-level "is this tile seamless" metric. Every cheap
# formulation (seam difference vs interior mean, roll-and-compare) fires on brick
# and water, whose own mortar and ripple periods make a correct seam look like a
# discontinuity — it reports "cannot tell" as "broken". The tile invariants below
# are the exact ones instead: primitives wrap, and band periods divide the tile.
# --------------------------------------------------------------------------------
def _silhouette(arr):
    """The alpha mask — the shape alone, with all colour and interior detail gone."""
    return arr[..., 3] > 0


def _worst_silhouette_gap(renders):
    import itertools
    import numpy as np
    sils = {k: _silhouette(v) for k, v in renders.items()}
    return min(int(np.logical_xor(sils[a], sils[b]).sum())
               for a, b in itertools.combinations(sils, 2))


def test_quadruped_builds_differ_in_silhouette(contract):
    """Four beasts, four outlines. Was 46px worst-pair (one loaf, cosmetic knobs)."""
    from meristem_generators.creatures import build_quadruped
    renders = {b: build_quadruped(contract, {"build": b})
               for b in ("dog", "wolf", "boar", "cat")}
    gap = _worst_silhouette_gap(renders)
    assert gap >= 100, f"closest pair differs by only {gap}px of silhouette"


def test_flyer_builds_differ_in_silhouette(contract):
    """bird and moth used to be the same ellipse pair; their only difference was
    interior feather lines, which are invisible in a 32px silhouette."""
    from meristem_generators.creatures import build_flyer
    renders = {b: build_flyer(contract, {"build": b}) for b in ("bat", "bird", "moth")}
    gap = _worst_silhouette_gap(renders)
    assert gap >= 90, f"closest pair differs by only {gap}px of silhouette"


def test_blade_family_scales_by_guard_span(contract):
    """dagger/sword/greatsword were one drawing at three scales. What separates them
    to the eye at 16px is how far the guard overhangs the blade."""
    from meristem_generators.items import weapon
    widths = {k: int(_silhouette(weapon(contract, {"kind": k})).any(axis=0).sum())
              for k in ("dagger", "sword", "greatsword")}
    assert widths["dagger"] < widths["sword"] < widths["greatsword"], widths
    assert widths["greatsword"] >= widths["dagger"] * 2, widths


def test_pickup_default_colour_is_per_shape(contract):
    """Every shape defaulted to one gold, so the library had a gold heart and a gold
    skull. A pickup's colour is part of its identity."""
    import numpy as np
    from meristem_generators.items import _PICKUP_COLORS, pickup

    def colours(arr):
        return {tuple(int(c) for c in px[:3]) for px in arr[arr[..., 3] == 255]}

    gold = _PICKUP_COLORS["coin"]
    for shape in ("heart", "gem", "skull", "key"):
        seen = colours(pickup(contract, {"shape": shape}))
        assert _PICKUP_COLORS[shape] in seen, f"{shape} does not draw its own colour"
        assert gold not in seen, f"{shape} still renders in the coin's gold"
    # an explicit colour still overrides the per-shape default
    assert not np.array_equal(pickup(contract, {"shape": "heart"}),
                              pickup(contract, {"shape": "heart", "color": (60, 90, 220)}))


def test_pickup_skull_honours_its_colour_knob(contract):
    """It accepted `color` and hardcoded bone, so recolouring a skull did nothing."""
    import numpy as np
    from meristem_generators.items import pickup
    assert not np.array_equal(pickup(contract, {"shape": "skull"}),
                              pickup(contract, {"shape": "skull", "color": (90, 160, 110)}))


def test_chest_lid_reads_as_separate_from_the_body(contract):
    """Closed: a wide dark seam where the lid meets the body. Open: a lit interior.
    Lid and body used to be one flat wood.base with no seam, so every build read as
    a plank with two stripes and `open` merely swapped in a yellow band."""
    import numpy as np
    from meristem_generators.items import _CHEST_BUILDS, chest
    from meristem_generators.sprite import outline_dark
    closed = chest(contract, {"build": "wood"})
    opened = chest(contract, {"build": "wood", "open": True})
    dark = outline_dark(_CHEST_BUILDS["wood"]["wood"])
    seam = sum(1 for c in range(closed.shape[1])
               if closed[8, c][3] == 255 and tuple(int(v) for v in closed[8, c][:3]) == dark)
    assert seam >= 8, f"closed chest has no lid seam ({seam}px of dark on row 8)"
    treasure = (opened[..., :3] == np.array([255, 226, 120])).all(axis=2)
    assert int(treasure.sum()) >= 6, "open chest shows no contents"


def test_tile_primitives_wrap_around_the_torus():
    """A tile is a torus. Anything that draws on it must wrap, not clamp."""
    import numpy as np
    from meristem_generators.procedural import _disc, _put
    img = np.zeros((16, 16, 4), dtype=np.uint8)
    _put(img, -1, -1, (255, 0, 0))
    assert tuple(int(v) for v in img[15, 15][:3]) == (255, 0, 0)
    _put(img, 16, 16, (0, 255, 0))
    assert tuple(int(v) for v in img[0, 0][:3]) == (0, 255, 0)
    img[:] = 0
    _disc(img, 0, 0, 2.0, (0, 0, 255))
    for y, x in ((0, 0), (15, 0), (0, 15), (15, 15)):   # a disc on the origin hits all corners
        assert tuple(int(v) for v in img[y, x][:3]) == (0, 0, 255), (y, x)


def test_cracks_wrap_instead_of_piling_on_the_border():
    """The exact regression: the crack walk clamped (`min(w-1, max(0, x))`), so a
    crack that ran off an edge stacked its remaining pixels against that edge — a
    dark smudge that repeated at every tile boundary, plainly visible in a 3x3
    preview of `stone`. Started near the bottom, a crack must CONTINUE at the top."""
    import numpy as np
    from meristem_generators.procedural import _cracks
    from meristem_generators.shading import Ramp

    class _ScriptedRng:
        def __init__(self, values):
            self._values = list(values)

        def integers(self, lo, hi=None):
            return self._values.pop(0)

    #        x=3  y=14  vertical  len=4   then dx=0 per step
    rng = _ScriptedRng([3, 14, 1, 4, 0, 0, 0, 0])
    img = np.zeros((16, 16, 4), dtype=np.uint8)
    _cracks(img, Ramp((150, 150, 160)), rng, 1)
    assert img[15, 3][3] == 255, "crack did not reach the bottom row"
    assert img[0, 3][3] == 255 and img[1, 3][3] == 255, "crack clamped instead of wrapping"


def test_periodic_tile_features_divide_the_tile(contract):
    """Band spacing must divide the tile height, or the courses collide at the seam."""
    from meristem_generators.procedural import RIPPLE_PERIOD, WAVE_PERIOD
    _, h = contract.canvas_of("terrain_tile")
    assert h % WAVE_PERIOD == 0, (h, WAVE_PERIOD)
    assert h % RIPPLE_PERIOD == 0, (h, RIPPLE_PERIOD)


def _apex_ratio(arr):
    """How pointed the top is: mean width of the top three rows over the widest row.
    A dome and a hood both taper, but a hood tapers to a POINT and keeps widening."""
    import numpy as np
    widths = (arr[..., 3] > 0).sum(axis=1)
    rows = np.flatnonzero(widths)
    return float(widths[rows[0]:rows[0] + 3].mean() / widths.max())


def test_specter_hood_tapers_to_a_point(contract):
    """A specter is a hooded figure; a `ghost` is a draped sheet. The specter was
    built as a dome on a straight rectangle, giving it the same blunt top as the
    sheet ghost (apex ratio 0.378 vs the ghost's 0.368) — on screen it read as a grey
    pillar with two red dots, not a cowl. Note this is NOT expressible as a silhouette
    XOR threshold: the fix moved ghost/specter from 96px apart to 74px while making
    them far easier to tell apart, because the useful difference is WHERE the shape
    narrows, not how many pixels disagree."""
    from meristem_generators.creatures import build_ghost
    specter = _apex_ratio(build_ghost(contract, {"build": "specter", "color": (150, 150, 180)}))
    sheet = _apex_ratio(build_ghost(contract, {"build": "ghost", "color": (224, 228, 244)}))
    assert specter <= 0.25, f"specter hood is blunt, not pointed (apex ratio {specter:.3f})"
    assert sheet >= 0.30, f"the sheet ghost should stay domed (apex ratio {sheet:.3f})"


def test_projectile_kinds_differ_in_silhouette(contract):
    """`bolt` was a 4-pointed star, which is exactly what `shuriken` is (37px apart),
    and `arrow` and `knife` were the same 2px diagonal with a block on one end (16px
    apart — the closest pair in the library). Bolt is now a lightning zigzag, and the
    arrow/knife pair is separated by length and by what is on each end."""
    from meristem_generators.items import projectile
    renders = {k: projectile(contract, {"kind": k})
               for k in ("arrow", "fireball", "bolt", "knife", "shuriken")}
    gap = _worst_silhouette_gap(renders)
    assert gap >= 26, f"closest projectile pair differs by only {gap}px of silhouette"
