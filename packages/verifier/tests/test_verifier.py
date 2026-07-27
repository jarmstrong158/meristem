import json
import os
from pathlib import Path

import pytest

from meristem_verifier import derive_assertions, run_assertions, capture_frame
from meristem_verifier.critique import visual_expectations

MANIFEST = Path(__file__).resolve().parents[3] / "examples" / "slice-01" / "manifest.json"
GODOT = os.environ.get("MERISTEM_GODOT")


def _can_render() -> bool:
    """Whether the VISUAL loop can run here, which is a different question from whether
    a Godot binary exists.

    The assertion loop runs under true `--headless` and needs nothing but the binary.
    The visual loop runs Godot WINDOWED on purpose, because `--headless` uses dummy
    drivers that do not render at all (dec-0007) — so it also needs a real display.
    Gating both on MERISTEM_GODOT alone meant that switching the assertion loop on in
    CI would switch on a capture that cannot possibly work there."""
    if not GODOT:
        return False
    return os.name == "nt" or bool(os.environ.get("DISPLAY"))


def _domains():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["domains"]


# ---- always-on unit tests ----
def test_derive_move_speed_assertion():
    a = derive_assertions(_domains())
    speed = [x for x in a if x["kind"] == "move_speed"]
    assert len(speed) == 1 and speed[0]["expected"] == 80.0


def test_derive_melee_damage_assertion():
    """If the spec gives the player an atk, hitting an enemy must reduce that enemy's
    hp by it. Checking the generated script for the right strings only proves the code
    was written; this assertion proves the swing CONNECTS in the engine — and it is
    what caught a reach shorter than the distance two colliding bodies settle at, an
    attack that read as correct and could never land."""
    a = derive_assertions(_domains())
    melee = [x for x in a if x["kind"] == "melee_damage"]
    assert len(melee) == 1
    assert melee[0]["entity"] == "slime"
    assert melee[0]["attack"] == 4 and melee[0]["enemy_hp"] == 8
    assert melee[0]["expected"] == 4                    # 8 hp - 4 atk


def test_derive_ability_damage_for_a_projectile_slot():
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "ability_damage"]
    assert len(got) == 1
    assert got[0]["ability"] == "firebolt" and got[0]["slot"] == 0
    # firebolt is power 4 scaling off mag, and the hero's mag is 3
    assert got[0]["power"] == 7 and got[0]["expected"] == 1       # 8 hp - 7


def test_no_ability_assertion_for_a_player_with_none():
    d = _domains()
    d["entities"]["characters"][0]["abilities"] = []
    assert [x for x in derive_assertions(d) if x["kind"] == "ability_damage"] == []


def test_derive_gear_bonus_for_a_worn_item_with_atk():
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "gear_bonus"]
    assert len(got) == 1
    assert got[0]["item"] == "sword" and got[0]["slot"] == "weapon"
    assert got[0]["base_atk"] == 4 and got[0]["bonus"] == 2
    assert got[0]["expected"] == 6


def test_no_gear_assertion_for_an_item_that_grants_nothing():
    d = _domains()
    d["items"]["items"][0]["stats"] = {}
    assert [x for x in derive_assertions(d) if x["kind"] == "gear_bonus"] == []


def test_derive_ability_cost_only_when_there_is_a_pool_to_spend():
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "ability_cost"]
    assert len(got) == 1
    assert got[0]["ability"] == "firebolt" and got[0]["cost"] == 2
    assert got[0]["pool"] == 10 and got[0]["expected"] == 8
    d = _domains()
    d["entities"]["characters"][0]["stats"].pop("mp")
    assert [x for x in derive_assertions(d) if x["kind"] == "ability_cost"] == []


def test_derive_loot_drop_only_for_a_guaranteed_single_drop():
    """A weighted roll is not deterministic, and an assertion that passes most of the
    time is worse than none — so only a table with one certain drop is asserted on."""
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "loot_drop"]
    assert len(got) == 1
    assert got[0]["entity"] == "slime" and got[0]["expected"] == "sword"

    chancy = _domains()
    chancy["items"]["drop_tables"][0]["nothing_weight"] = 3
    assert [x for x in derive_assertions(chancy) if x["kind"] == "loot_drop"] == []

    multi = _domains()
    multi["items"]["drop_tables"][0]["drops"].append({"item_id": "sword", "weight": 1})
    assert [x for x in derive_assertions(multi) if x["kind"] == "loot_drop"] == []


def test_derive_tile_collision_from_the_first_wall_pair():
    """Finds a passable cell whose right neighbour is solid — in the slice that is the
    grass beside the pond."""
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "tile_collision"]
    assert len(got) == 1
    x, y = got[0]["from"]
    lv = _domains()["levels"]["levels"][0]
    legend = lv["legend"]
    assert legend[lv["rows"][y][x]] not in ("water", "stone", "brick", "lava")
    assert legend[lv["rows"][y][x + 1]] in ("water", "stone", "brick", "lava")
    assert got[0]["boundary_x"] == (x + 1) * 16


def test_no_tile_collision_assertion_without_a_wall():
    """A map with nothing solid in it has no claim to make."""
    d = _domains()
    lv = d["levels"]["levels"][0]
    lv["legend"] = {ch: "grass" for ch in lv["legend"]}
    assert [x for x in derive_assertions(d) if x["kind"] == "tile_collision"] == []


def test_derive_room_transition_only_when_a_level_has_exits():
    d = _domains()
    assert [x for x in derive_assertions(d) if x["kind"] == "room_transition"] == []
    d["levels"]["levels"][0]["exits"] = [{"x": 1, "y": 1, "to": "elsewhere"}]
    got = [x for x in derive_assertions(d) if x["kind"] == "room_transition"]
    assert len(got) == 1
    assert got[0]["from_scene"] == "res://scenes/main.tscn"   # the start room
    assert got[0]["doors"] == 1


def test_no_melee_assertion_without_the_stats_to_check():
    d = _domains()
    d["entities"]["characters"][0]["stats"].pop("atk")
    assert [x for x in derive_assertions(d) if x["kind"] == "melee_damage"] == []


def test_no_assertions_without_matching_archetype():
    d = _domains()
    d["project"]["control_scheme"] = "does_not_exist"
    assert derive_assertions(d) == []


def test_visual_expectations_mentions_entities_and_palette():
    exp = " ".join(visual_expectations(_domains()))
    assert "PICO-8" in exp
    assert "Hero" in exp and "Slime" in exp
    assert "water" in exp.lower()          # enemy-not-on-water check present


# ---- real-engine tests (opt-in) ----
@pytest.fixture(scope="module")
def compiled(tmp_path_factory):
    from meristem_compiler.compile import compile_project
    out = tmp_path_factory.mktemp("verify-slice")
    compile_project(MANIFEST, out)
    return out


@pytest.mark.skipif(not GODOT, reason="set MERISTEM_GODOT to run the engine assertion loop")
def test_assertion_loop_measures_move_speed(compiled):
    res = run_assertions(compiled, derive_assertions(_domains()), GODOT)
    assert res["ok"], res
    r = res["results"][0]
    assert abs(r["measured"] - 80.0) <= 6.4


@pytest.mark.skipif(not _can_render(),
                    reason="the visual capture runs Godot windowed and needs a real "
                           "display (set MERISTEM_GODOT, and DISPLAY on POSIX)")
def test_visual_capture_produces_png(compiled):
    cap = capture_frame(compiled, GODOT)
    assert cap is not None and cap.exists()
    assert cap.stat().st_size > 200          # a real, non-empty PNG


def test_derive_stat_scaling_covers_base_and_gear():
    """The chain this proves is manifest stat -> gear bonus -> cast-time read. Every
    link is invisible from outside the engine: a shot that lands for its BASE power
    looks identical on screen to one that scaled correctly."""
    got = [x for x in derive_assertions(_domains()) if x["kind"] == "stat_scaling"]
    assert len(got) == 1
    a = got[0]
    assert a["ability"] == "firebolt" and a["stat"] == "mag"
    assert a["power"] == 4 and a["base"] == 3
    assert a["expected"] == 7                       # power 4 + the hero's mag 3
    assert a["item"] == "focus_charm" and a["bonus"] == 2
    assert a["expected_equipped"] == 9              # ...and +2 more wearing the charm


def test_no_stat_scaling_assertion_when_nothing_scales():
    """An assertion derived for a game that does not use the feature would be noise,
    and one that silently passed on an empty check would be worse."""
    domains = _domains()
    for ab in domains["abilities"]["abilities"]:
        ab.pop("scaling", None)
    assert not [x for x in derive_assertions(domains) if x["kind"] == "stat_scaling"]
