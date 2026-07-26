import json
import os
import subprocess
from pathlib import Path

import pytest

from meristem_compiler.compile import CompileError, compile_project
from meristem_spec_store import SpecStore

MANIFEST = Path(__file__).resolve().parents[3] / "examples" / "slice-01" / "manifest.json"


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    out = tmp_path_factory.mktemp("slice")
    compile_project(MANIFEST, out)
    return out


def two_room_manifest(tmp_path: Path) -> Path:
    """The slice manifest with a second level and a door each way. Shared by the
    compiler tests and (via the same helper) the verifier's engine test."""
    store = SpecStore.load(MANIFEST)
    levels = store.get("levels")
    first = levels["levels"][0]
    w = len(first["rows"][0])
    cave = {
        "id": "cave_01",
        "region": first["region"],
        "legend": {".": "stone", "~": "water"},
        "rows": ["." * w for _ in range(8)],
        "player_spawn": {"x": 2, "y": 2},
        "spawns": [],
        "exits": [{"x": 1, "y": 1, "to": first["id"], "to_spawn": {"x": 3, "y": 3}}],
    }
    first["exits"] = [{"x": 2, "y": 2, "to": "cave_01"}]      # no to_spawn -> cave default
    levels["levels"].append(cave)
    store.set_domain("levels", levels, {"actor": "test"})
    world = store.get("world")
    for r in world["regions"]:
        if r["id"] == first["region"]:
            r.setdefault("levels", []).append("cave_01")
    store.set_domain("world", world, {"actor": "test"})
    out = tmp_path / "two_room.manifest.json"
    store.save(out)
    return out


def test_two_room_manifest_compiles_both_rooms(tmp_path):
    """Levels used to be compiled one at a time — `pick_level` chose the first and the
    rest of the manifest's rooms were silently never built."""
    manifest = two_room_manifest(tmp_path)
    assert SpecStore.load(manifest).validate_all().ok
    out = tmp_path / "build"
    compile_project(manifest, out)
    # a scene per room; the start keeps the name main.tscn so it stays the entry point
    assert (out / "scenes" / "main.tscn").exists()
    assert (out / "scenes" / "level_cave_01.tscn").exists()
    # and a runtime grid per room
    assert (out / "levels" / "grove_01.grid.json").exists()
    assert (out / "levels" / "cave_01.grid.json").exists()
    # one shared world.gd, told which grid to build by the scene
    world = (out / "scripts" / "world.gd").read_text(encoding="utf-8")
    assert "@export var level_name" in world and "grove_01" not in world
    assert 'level_name = "grove_01"' in (out / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'level_name = "cave_01"' in (out / "scenes" / "level_cave_01.tscn").read_text(encoding="utf-8")


def test_doors_bake_target_scene_and_arrival(tmp_path):
    manifest = two_room_manifest(tmp_path)
    out = tmp_path / "build"
    compile_project(manifest, out)
    assert (out / "scripts" / "door.gd").exists()
    main = (out / "scenes" / "main.tscn").read_text(encoding="utf-8")
    cave = (out / "scenes" / "level_cave_01.tscn").read_text(encoding="utf-8")
    assert 'to_scene = "res://scenes/level_cave_01.tscn"' in main
    # grove's exit gave no to_spawn, so it defaults to the cave's own player_spawn (2,2)
    assert "to_spawn = Vector2(40, 48)" in main
    # the cave's door goes back and names an explicit arrival cell (3,3)
    assert 'to_scene = "res://scenes/main.tscn"' in cave
    assert "to_spawn = Vector2(56, 64)" in cave
    # state that must survive a room change lives on the autoload
    gs = (out / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert "func go_to_room" in gs and "func take_pending_spawn" in gs
    player = (out / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert "Game.take_pending_spawn()" in player


def test_exit_to_an_unknown_level_is_refused(tmp_path):
    """Cross-ref catches this first; the compiler must not build a dead doorway even
    if it is somehow reached with one."""
    from meristem_compiler.compile import compile_project as cp
    store = SpecStore.load(MANIFEST)
    levels = store.get("levels")
    levels["levels"][0]["exits"] = [{"x": 1, "y": 1, "to": "nowhere"}]
    store.set_domain("levels", levels, {"actor": "test"})
    bad = tmp_path / "bad_exit.manifest.json"
    store.save(bad)
    report = SpecStore.load(bad).validate_all()
    assert not report.ok
    assert any("nowhere" in e for e in report.crossref_errors)
    with pytest.raises(CompileError):
        cp(bad, tmp_path / "out")


def _platformer_manifest(tmp_path: Path) -> Path:
    """The slice manifest with its controller switched to a platformer. Keeps the
    archetype id so entities' behavior_archetype refs still resolve — i.e. a manifest
    that validate_all considers completely valid."""
    store = SpecStore.load(MANIFEST)
    mech = store.get("mechanics")
    mech["archetypes"][0]["kind"] = "platformer_controller"
    mech["archetypes"][0]["params"] = {"move_speed": 120, "accel": 900,
                                       "jump_height": 48, "gravity": 980,
                                       "coyote_time": 0.1, "jump_buffer": 0.1,
                                       "air_control": 0.8}
    store.set_domain("mechanics", mech, {"actor": "test"})
    out = tmp_path / "platformer.manifest.json"
    store.save(out)
    return out


def test_valid_platformer_manifest_is_refused_not_silently_built(tmp_path):
    """The regression: `write_scripts` rendered the top-down template regardless of
    kind, so this manifest compiled "successfully" into a game with no gravity and no
    jump, silently discarding jump_height and gravity and inventing a FRICTION constant
    the platformer schema does not even allow."""
    manifest = _platformer_manifest(tmp_path)
    store = SpecStore.load(manifest)
    assert store.validate_all().ok                       # the SPEC is fine...
    with pytest.raises(CompileError) as exc:             # ...the COMPILER must say no
        compile_project(manifest, tmp_path / "build")
    msg = str(exc.value)
    assert "platformer_controller" in msg
    assert "top_down_controller" in msg                  # names what IS implemented
    assert "compiler gap, not a spec error" in msg       # does not blame the manifest


def test_refusal_happens_before_any_output_is_written(tmp_path):
    """A dead end should not first generate every asset and write the level."""
    manifest = _platformer_manifest(tmp_path)
    out = tmp_path / "build"
    with pytest.raises(CompileError):
        compile_project(manifest, out)
    assert not (out / "assets").exists()
    assert not (out / "scripts").exists()


def test_controller_params_cannot_leak_between_kinds():
    """Each controller substitutes only its OWN declared params, so a default from one
    can never end up baked into another's script."""
    from meristem_compiler.scenes import CONTROLLERS
    _, defaults = CONTROLLERS["top_down_controller"]
    assert {"move_speed", "accel", "friction"} <= set(defaults)
    # nothing platformer-only may appear among a top-down controller's substitutions
    assert not ({"jump_height", "gravity", "coyote_time", "air_control"} & set(defaults))
    assert "platformer_controller" not in CONTROLLERS   # not implemented -> not offered


def test_player_can_actually_fight_back(project):
    """Before this, the player had no attack at all and enemy `hp` was exported but
    never read by anything — you could only be hurt by walking into things."""
    gd = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert 'Input.is_action_just_pressed("attack")' in gd
    assert "func _swing()" in gd
    assert "take_damage(ATTACK_DAMAGE)" in gd
    assert "ATTACK_DAMAGE: int = 4" in gd            # the player entity's atk stat
    # the swing is directional: you cannot hit what is behind you
    assert "_facing" in gd and "dot(_facing)" in gd
    # and it is rate-limited
    assert "_attack_cd" in gd and "ATTACK_COOLDOWN" in gd


def test_enemies_take_damage_and_die(project):
    gd = (project / "scripts" / "enemy_slime.gd").read_text(encoding="utf-8")
    assert "func take_damage(amount: int)" in gd
    assert "Game.register_kill()" in gd and "queue_free()" in gd
    state = (project / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert "signal enemy_killed(total: int)" in state
    assert "func register_kill()" in state
    assert "kills = 0" in state                      # a death resets the run's tally
    hud = (project / "scripts" / "hud.gd").read_text(encoding="utf-8")
    assert "Game.enemy_killed.connect" in hud
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'name="KillLabel"' in main                # the label the HUD binds to exists


def test_enemy_ai_archetype_selects_its_template(tmp_path):
    """`ai` picks a real behaviour script, and its tuning comes from the entity's own
    stats rather than the mechanics archetype."""
    from meristem_compiler.scenes import ENEMY_AI, write_scripts
    assert set(ENEMY_AI) == {"idle", "patrol", "chase"}
    enemies = [
        {"id": "bobber", "name": "Bobber", "hp": 3, "atk": 1, "ai": "idle", "stats": {}},
        {"id": "walker", "name": "Walker", "hp": 4, "atk": 2, "ai": "patrol",
         "stats": {"speed": 55, "patrol_distance": 72}},
        {"id": "hunter", "name": "Hunter", "hp": 5, "atk": 3, "ai": "chase",
         "stats": {"speed": 44, "aggro_radius": 130}},
    ]
    write_scripts(tmp_path, kind="top_down_controller", params={},
                  enemies=enemies, player_hp=10, player_atk=2)
    sd = tmp_path / "scripts"
    idle = (sd / "enemy_bobber.gd").read_text(encoding="utf-8")
    patrol = (sd / "enemy_walker.gd").read_text(encoding="utf-8")
    chase = (sd / "enemy_hunter.gd").read_text(encoding="utf-8")
    assert "ai: idle" in idle and "SPEED" not in idle
    assert "ai: patrol" in patrol
    assert "SPEED: float = 55.0" in patrol and "PATROL_DISTANCE: float = 72.0" in patrol
    assert "ai: chase" in chase
    assert "SPEED: float = 44.0" in chase and "AGGRO_RADIUS: float = 130.0" in chase
    # every archetype is damageable and reports its death
    for gd in (idle, patrol, chase):
        assert "func take_damage(amount: int)" in gd and "Game.register_kill()" in gd
    # an unstated ai is the placeholder, not a crash
    write_scripts(tmp_path, kind="top_down_controller", params={},
                  enemies=[{"id": "plain", "name": "Plain", "hp": 1, "atk": 1}],
                  player_hp=10, player_atk=1)
    assert "ai: idle" in (sd / "enemy_plain.gd").read_text(encoding="utf-8")


def test_unimplemented_enemy_ai_is_refused(tmp_path):
    """As with the controller: a missing template must not silently downgrade a
    chaser to a bobbing placeholder."""
    from meristem_compiler.compile import _enemy_ai
    assert _enemy_ai({"id": "e", "ai": "chase"}) == "chase"
    assert _enemy_ai({"id": "e"}) == "idle"                 # unstated -> placeholder
    with pytest.raises(CompileError) as exc:
        _enemy_ai({"id": "boss", "ai": "flying_swarm"})
    assert "flying_swarm" in str(exc.value) and "chase" in str(exc.value)


def test_project_godot_written(project):
    txt = (project / "project.godot").read_text(encoding="utf-8")
    assert 'config/name="Slime Grove"' in txt
    assert 'run/main_scene="res://scenes/main.tscn"' in txt
    assert "move_up=" in txt and "move_left=" in txt          # input map present
    assert "default_texture_filter=0" in txt                  # pixel-art nearest


def test_all_assets_and_sidecars(project):
    a = project / "assets"
    pngs = sorted(p.name for p in a.glob("*.png"))
    # 9 base + 4 player-walk + 3 enemy idle-anim + 3 coin spin + the level's sand tile
    assert len(pngs) == 20
    for png in pngs:
        assert (a / f"{png}.prov.json").exists()
    # provenance backend is now the archetype the sprite was built from (dec-0022)
    prov = json.loads((a / "char_player_idle.png.prov.json").read_text())
    assert prov["backend"] == "humanoid"
    tprov = json.loads((a / "tile_grass.png.prov.json").read_text())
    assert tprov["backend"] == "tile"


def test_player_is_animated(project):
    frames = (project / "scenes" / "player_frames.tres").read_text(encoding="utf-8")
    assert frames.count("_walk_") == 4          # four walk-cycle frame textures
    assert '&"idle"' in frames and '&"walk"' in frames
    assert "AnimatedSprite2D" in (project / "scenes" / "player.tscn").read_text(encoding="utf-8")
    for i in range(4):
        assert (project / "assets" / f"char_player_walk_{i}.png").exists()


def test_enemy_and_coin_animated(project):
    # the blob enemy animates: SpriteFrames + AnimatedSprite2D + idle-anim frames
    ef = (project / "scenes" / "enemy_slime_frames.tres").read_text(encoding="utf-8")
    assert '&"idle"' in ef and ef.count("enemy_slime_") == 4          # idle + 3 anim frames
    assert "AnimatedSprite2D" in (project / "scenes" / "enemy_slime.tscn").read_text(encoding="utf-8")
    for i in (1, 2, 3):
        assert (project / "assets" / f"enemy_slime_anim_{i}.png").exists()
    # the HUD coin spins
    cf = (project / "scenes" / "coin_frames.tres").read_text(encoding="utf-8")
    assert '&"spin"' in cf and cf.count("ui_coin") == 4               # idle + 3 spin frames
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'type="AnimatedSprite2D" parent="HUD"' in main


def test_authored_level_projects(project):
    # the manifest's authored layout — not a synthesized one — is what compiles:
    # the sand marker patch (rows 9-10, cols 16-17) must appear in the runtime grid
    # and the .ldtk, and the sand tile asset must have been emitted.
    grid = json.loads((project / "levels" / "grove_01.grid.json").read_text())["grid"]
    assert grid[9][16] == "sand" and grid[10][17] == "sand"
    assert grid[0][0] == "grass" and grid[6][0] == "dirt"
    assert (project / "assets" / "tile_sand.png").exists()
    doc = json.loads((project / "levels" / "grove_01.ldtk").read_text(encoding="utf-8"))
    li = {l["__identifier"]: l for l in doc["levels"][0]["layerInstances"]}
    from meristem_compiler.level import SEMANTIC
    csv = li["Semantic"]["intGridCsv"]
    assert csv[9 * 20 + 16] == SEMANTIC["sand"]


def test_spawns_placed_in_main_scene(project):
    # two slime spawns + the placed sword from the authored level
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'name="Enemy0"' in main and 'name="Enemy1"' in main
    assert "Vector2(216, 144)" in main          # slime at cell (13,8) -> feet px
    assert "Vector2(280, 48)" in main           # slime at cell (17,2)
    assert 'name="Item0"' in main and "pickup_sword.tscn" in main   # the sword pickup
    assert 'name="Player"' in main and "Vector2(72, 96)" in main   # player_spawn (4,5)


def test_playable_loop_wiring(project):
    # the compiled game is a loop, not a diorama: collectable items, contact
    # damage, hp/collect HUD, death -> reload — all deterministic template code.
    pick = (project / "scenes" / "pickup_sword.tscn").read_text(encoding="utf-8")
    assert 'type="Area2D"' in pick and 'item_id = "sword"' in pick
    assert "icon_sword.png" in pick and "pickup.gd" in pick
    gs = (project / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert "max_hp: int = 20" in gs                 # player hp from the manifest
    assert "reload_current_scene" in gs             # death restarts the run
    player = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert 'is_in_group("enemies")' in player and "Game.take_damage" in player
    enemy = (project / "scripts" / "enemy_slime.gd").read_text(encoding="utf-8")
    assert 'add_to_group("enemies")' in enemy
    proj = (project / "project.godot").read_text(encoding="utf-8")
    assert 'Game="*res://scripts/game_state.gd"' in proj    # autoload registered
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert "hud.gd" in main and 'name="HpLabel"' in main and 'name="ItemLabel"' in main


def test_ldtk_valid(project):
    doc = json.loads((project / "levels" / "grove_01.ldtk").read_text(encoding="utf-8"))
    assert doc["jsonVersion"] == "1.5.3"
    assert doc["externalLevels"] is False
    li = {l["__identifier"]: l for l in doc["levels"][0]["layerInstances"]}
    assert len(li["Ground"]["gridTiles"]) == 240
    assert len(li["Semantic"]["intGridCsv"]) == 240
    # uid links resolve
    ts = doc["defs"]["tilesets"][0]
    assert li["Ground"]["__tilesetDefUid"] == ts["uid"]
    assert (project / "levels" / "tileset.png").exists()


def test_scripts_substituted(project):
    gd = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert "{{" not in gd and "}}" not in gd
    assert "MOVE_SPEED: float = 80.0" in gd
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    for ref in ("player.tscn", "enemy_slime.tscn", "world.gd", "ui_heart.png"):
        assert ref in main


def test_archetype_dispatch_from_spec(tmp_path):
    # change the enemy's sprite archetype in the spec -> the compiler builds that archetype
    from meristem_spec_store import SpecStore
    store = SpecStore.load(MANIFEST)
    ents = store.get("entities")
    ents["enemies"][0]["sprite"] = {"archetype": "ghost", "config": {"color": [220, 225, 244]}}
    store.set_domain("entities", ents)
    p = tmp_path / "ghost.manifest.json"
    store.save(p)
    out = tmp_path / "ghost-out"
    compile_project(p, out)
    prov = json.loads((out / "assets" / "enemy_slime_idle.png.prov.json").read_text())
    assert prov["backend"] == "ghost"          # built from the ghost archetype, not blob


# The schema-enum/registry drift test lives with the schemas it guards, in
# packages/spec-store/tests/test_schemas.py (per-file, both directions, plus an
# enum-vs-enum agreement check). It used to be duplicated here.


def test_empty_manifest_is_refused_with_an_actionable_error(tmp_path):
    """`validate_all` only iterated the domains that were PRESENT, so an empty
    manifest was ok=True and the compiler died on domains["project"] with a bare
    KeyError. It must now name the domains the author has to supply."""
    p = SpecStore().save(tmp_path / "empty.manifest.json")
    with pytest.raises(CompileError) as ei:
        compile_project(p, tmp_path / "out")
    assert "missing required domain" in str(ei.value)
    assert "project" in str(ei.value)


def test_invalid_manifest_refused(tmp_path):
    store = SpecStore.load(MANIFEST)
    bad_items = store.get("items")
    bad_items["drop_tables"][0]["enemy_id"] = "dragon"   # dangling cross-ref (schema-valid)
    store.set_domain("items", bad_items)
    bad_path = tmp_path / "bad.manifest.json"
    store.save(bad_path)
    with pytest.raises(CompileError):
        compile_project(bad_path, tmp_path / "out")


@pytest.mark.skipif(not os.environ.get("MERISTEM_GODOT"),
                    reason="set MERISTEM_GODOT to a Godot 4.x binary to run the engine smoke test")
def test_room_transition_verified_in_engine(tmp_path):
    """Doors are only real if their baked res:// path resolves and the arrival handoff
    lands. A wrong path is invisible until someone walks into the doorway, and no
    amount of checking the .tscn text catches it."""
    from meristem_verifier.assertions import derive_assertions
    from meristem_verifier.runner import run_assertions
    manifest = two_room_manifest(tmp_path)
    out = tmp_path / "build"
    compile_project(manifest, out)
    asserts = [a for a in derive_assertions(SpecStore.load(manifest).get_all())
               if a["kind"] == "room_transition"]
    assert asserts, "no room_transition assertion derived for a manifest with exits"
    res = run_assertions(out, asserts, os.environ["MERISTEM_GODOT"])
    assert res["ok"], res


@pytest.mark.skipif(not os.environ.get("MERISTEM_GODOT"),
                    reason="set MERISTEM_GODOT to a Godot 4.x binary to run the engine smoke test")
def test_godot_imports_and_runs(project):
    godot = os.environ["MERISTEM_GODOT"]
    imp = subprocess.run([godot, "--headless", "--path", str(project), "--import"],
                         capture_output=True, text=True, timeout=120)
    assert imp.returncode == 0, imp.stderr
    run = subprocess.run([godot, "--headless", "--path", str(project), "--quit-after", "5"],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    assert "SCRIPT ERROR" not in (run.stdout + run.stderr)
