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
    # The floor must be PASSABLE. This fixture originally laid the whole cave in
    # `stone`, which became a room that is entirely wall the moment solid tiles got
    # collision — the spawn and the door were both inside it, and nothing noticed until
    # cross-ref started checking. The stone patch is kept, away from both, so the test
    # still covers a second level pulling an extra tile into the tileset.
    floor = "." * w
    wall_row = "." * 8 + "##" + "." * (w - 10)
    cave = {
        "id": "cave_01",
        "region": first["region"],
        "legend": {".": "dirt", "#": "stone"},
        "rows": [floor, floor, floor, floor, wall_row, floor, floor, floor],
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


def test_abilities_compile_to_slots_and_scenes(project):
    """Abilities live on a child node, so they are not coupled to a control scheme and
    a second controller will not need its own copy of the ability code."""
    runner = (project / "scripts" / "ability_runner.gd").read_text(encoding="utf-8")
    assert '"id": "firebolt"' in runner and '"kind": "projectile"' in runner
    assert '"id": "mend"' in runner and '"kind": "heal"' in runner
    assert '"scene": "res://scenes/projectile_firebolt.tscn"' in runner
    # the runner implements every kind in the fixed library
    for kind in ("projectile", "melee_arc", "heal", "dash"):
        assert f'"{kind}"' in runner, kind
    # the projectile got its own scene with the authored numbers baked in
    proj = (project / "scenes" / "projectile_firebolt.tscn").read_text(encoding="utf-8")
    assert "speed = 140.0" in proj and "power = 4" in proj and "max_range = 120.0" in proj
    assert (project / "scripts" / "projectile.gd").exists()
    # the player scene mounts the runner, and the controller only forwards input
    player_scene = (project / "scenes" / "player.tscn").read_text(encoding="utf-8")
    assert 'name="Abilities"' in player_scene and "ability_runner.gd" in player_scene
    player = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert "_abilities.use(slot, _facing)" in player
    assert "ABILITY_SLOTS: int = 3" in player
    # and the input map binds the slots
    proj_godot = (project / "project.godot").read_text(encoding="utf-8")
    for n in (1, 2, 3):
        assert f"ability_{n}=" in proj_godot


def test_unimplemented_ability_kind_is_refused():
    """A slot bound to a kind the runner cannot execute would be pressable and silent.

    Exercised against `_player_abilities` directly rather than through a manifest,
    because `kind` is a schema enum — an unknown kind cannot reach the compiler through
    a stored manifest at all. This guards the case where the enum gains a kind before
    the runner implements it."""
    from meristem_compiler.compile import _player_abilities
    domains = {"abilities": {"abilities": [
        {"id": "summon_bat", "name": "Summon", "kind": "summon", "power": 1, "cooldown": 1}]}}
    player = {"id": "player", "abilities": ["summon_bat"]}
    with pytest.raises(CompileError) as exc:
        _player_abilities(domains, player, {})
    msg = str(exc.value)
    assert "summon" in msg and "compiler gap, not a spec error" in msg


def test_more_abilities_than_input_slots_is_refused(tmp_path):
    """An ability past the bound slots is unreachable, which is a spec that does not do
    what it says."""
    from meristem_compiler.compile import _player_abilities
    from meristem_compiler.scenes import ABILITY_SLOTS
    domains = {"abilities": {"abilities": [
        {"id": f"a{i}", "name": f"A{i}", "kind": "heal", "power": 1, "cooldown": 1}
        for i in range(ABILITY_SLOTS + 1)]}}
    player = {"id": "player", "abilities": [f"a{i}" for i in range(ABILITY_SLOTS + 1)]}
    with pytest.raises(CompileError) as exc:
        _player_abilities(domains, player, {})
    assert "unreachable" in str(exc.value)


def test_player_without_abilities_still_compiles(tmp_path):
    """The domain is optional; an empty slot table must not break the runner."""
    from meristem_compiler.scenes import write_scripts
    write_scripts(tmp_path, kind="top_down_controller", params={}, enemies=[],
                  player_hp=10, player_atk=2, abilities=[])
    runner = (tmp_path / "scripts" / "ability_runner.gd").read_text(encoding="utf-8")
    assert "const ABILITIES: Array = []" in runner
    assert not (tmp_path / "scripts" / "projectile.gd").exists()   # nothing fires


def test_solid_tiles_get_collision(project):
    """The ground builder made Sprite2D nodes and nothing else, so there was no
    collision anywhere: the player walked over water and stone, and the patrol AI's
    is_on_wall() could never be true. Level geometry was decoration."""
    world = (project / "scripts" / "world.gd").read_text(encoding="utf-8")
    assert "const SOLID: Array" in world
    for name in ("water", "stone", "brick", "lava"):
        assert f'"{name}"' in world, name
    assert "grass" not in world.split("const SOLID")[1].split("\n")[0]
    # one body carrying every wall shape, not a body per cell
    assert "StaticBody2D.new()" in world and 'walls.name = "Walls"' in world
    assert "RectangleShape2D.new()" in world
    assert "walls.add_child(shape)" in world
    # shape centres are offset half a tile, because tiles draw from their top-left
    assert "TILE / 2.0" in world


def test_spawns_on_impassable_terrain_are_refused(tmp_path):
    """The follow-up the visual loop earned when it caught an enemy standing on the
    water pond — a placement bug no physics assertion sees. Now that solid tiles carry
    collision, such a spawn is stuck inside a wall."""
    store = SpecStore.load(MANIFEST)
    levels = store.get("levels")
    lv = levels["levels"][0]
    # the pond: rows 2-3, x 13-16 in the slice's grove
    lv["spawns"].append({"id": "slime", "kind": "enemy", "x": 14, "y": 2})
    store.set_domain("levels", levels, {"actor": "test"})
    bad = tmp_path / "on_water.manifest.json"
    store.save(bad)
    report = SpecStore.load(bad).validate_all()
    assert not report.ok
    assert any("blocks movement" in e and "water" in e for e in report.crossref_errors), \
        report.crossref_errors
    with pytest.raises(CompileError):
        compile_project(bad, tmp_path / "out")


def test_player_spawn_and_doors_on_impassable_terrain_are_refused(tmp_path):
    store = SpecStore.load(MANIFEST)
    levels = store.get("levels")
    lv = levels["levels"][0]
    lv["player_spawn"] = {"x": 2, "y": 9}          # the stone block
    lv["exits"] = [{"x": 3, "y": 9, "to": lv["id"]}]
    store.set_domain("levels", levels, {"actor": "test"})
    bad = tmp_path / "stuck.manifest.json"
    store.save(bad)
    errs = SpecStore.load(bad).validate_all().crossref_errors
    assert any("player_spawn" in e and "blocks movement" in e for e in errs), errs
    assert any("exit" in e and "never be reached" in e for e in errs), errs


def test_drop_tables_reach_the_runtime(project):
    """`drop_tables` were authorable from the start and nothing dropped on kill."""
    gs = (project / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert "const DROPS: Dictionary" in gs
    assert '"slime"' in gs and '"item": "sword"' in gs
    assert "func drop_loot(enemy_id: String, at: Vector2)" in gs
    # the winning item is parented to the scene, not to the dying enemy
    assert "get_tree().current_scene" in gs
    # every AI archetype knows its own id and rolls before it is freed
    enemy = (project / "scripts" / "enemy_slime.gd").read_text(encoding="utf-8")
    assert 'ENEMY_ID: String = "slime"' in enemy
    assert "Game.drop_loot(ENEMY_ID, global_position)" in enemy
    assert enemy.index("Game.drop_loot") < enemy.index("queue_free()")


def test_every_ai_archetype_drops_loot():
    """The death block is repeated per template, so it is exactly the kind of thing that
    gets updated in one and forgotten in the others."""
    from meristem_compiler.scenes import ENEMY_AI, TEMPLATES
    for ai, (template, _) in ENEMY_AI.items():
        text = (TEMPLATES / template).read_text(encoding="utf-8")
        assert "Game.drop_loot(ENEMY_ID, global_position)" in text, ai
        assert 'ENEMY_ID: String = "{{id}}"' in text, ai


def test_loot_only_items_still_get_a_pickup_scene(tmp_path):
    """`drop_loot` loads pickup_<id>.tscn by name at runtime. Only PLACED items used to
    get a scene, so an item that exists purely as loot had nothing to spawn."""
    store = SpecStore.load(MANIFEST)
    items = store.get("items")
    items["items"].append({
        "id": "relic", "name": "Odd Relic", "slot": "accessory", "rarity": "common",
        "stats": {"def": 1},
        "sprite": {"archetype": "pickup", "config": {"shape": "gem"}}})
    items["drop_tables"].append({"enemy_id": "slime", "drops": [{"item_id": "relic", "weight": 1}]})
    store.set_domain("items", items, {"actor": "test"})
    out = tmp_path / "m.json"
    store.save(out)
    build = tmp_path / "build"
    compile_project(out, build)
    # never placed in any level, but droppable -> must have a scene to instantiate
    assert (build / "scenes" / "pickup_relic.tscn").exists()
    assert '"item": "relic"' in (build / "scripts" / "game_state.gd").read_text(encoding="utf-8")


def test_droppable_item_without_a_sprite_is_refused(tmp_path):
    """There would be nothing to spawn, and the failure would only appear on a kill."""
    store = SpecStore.load(MANIFEST)
    items = store.get("items")
    items["items"].append({"id": "ghostly", "name": "Ghostly Thing", "slot": "accessory",
                           "rarity": "common"})
    items["drop_tables"].append({"enemy_id": "slime",
                                 "drops": [{"item_id": "ghostly", "weight": 1}]})
    store.set_domain("items", items, {"actor": "test"})
    out = tmp_path / "m.json"
    store.save(out)
    with pytest.raises(CompileError) as exc:
        compile_project(out, tmp_path / "build")
    assert "ghostly" in str(exc.value) and "sprite" in str(exc.value)


def test_nothing_weight_is_carried_into_the_pool(tmp_path):
    """Without it every kill drops something, which is rarely what a game wants."""
    from meristem_compiler.compile import _drop_tables
    domains = {"items": {"drop_tables": [
        {"enemy_id": "slime", "nothing_weight": 3,
         "drops": [{"item_id": "sword", "weight": 1}]}]}}
    tables, droppable = _drop_tables(domains, {"sword": "icon_sword.png"})
    assert tables["slime"]["nothing"] == 3
    assert tables["slime"]["drops"] == [{"item": "sword", "weight": 1}]
    assert droppable == {"sword": "icon_sword.png"}
    # absent -> 0, i.e. a guaranteed drop
    plain = {"items": {"drop_tables": [
        {"enemy_id": "slime", "drops": [{"item_id": "sword", "weight": 1}]}]}}
    assert _drop_tables(plain, {"sword": "icon_sword.png"})[0]["slime"]["nothing"] == 0


def test_gear_stats_reach_the_runtime(project):
    """Item `slot` and `stats` were authorable from the beginning and compiled to
    nothing but a sprite and a placement. Now the item table is baked into Game, and
    the player asks Game.atk() every swing instead of carrying a frozen constant."""
    gs = (project / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert '"sword"' in gs and '"slot": "weapon"' in gs and '"atk": 2' in gs
    assert "func stat_bonus(stat: String)" in gs
    assert "func atk()" in gs and "func defense()" in gs
    assert "base_atk: int = 4" in gs and "base_def: int = 2" in gs
    # collecting equips, and only worn slots grant anything
    assert "_try_equip(item_id)" in gs
    assert 'EQUIP_SLOTS: Array = ["weapon", "armor", "accessory"]' in gs
    # defence applies, but a hit always lands
    assert "maxi(amount - defense(), 1)" in gs
    # the swing is no longer a baked constant
    player = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert "Game.atk()" in player
    assert "ATTACK_DAMAGE" not in player


def test_ability_cost_is_baked_and_charged(project):
    """The regression this shipped with for one commit: `cost` was in the schema and
    read by the runner, but never copied into the baked slot -- so the manifest said
    2 mp and the game charged nothing."""
    runner = (project / "scripts" / "ability_runner.gd").read_text(encoding="utf-8")
    assert '"cost": 2' in runner                       # firebolt's authored cost
    assert "Game.spend(int(a.get(" in runner
    gs = (project / "scripts" / "game_state.gd").read_text(encoding="utf-8")
    assert "func spend(cost: int) -> bool" in gs
    assert "max_mp: int = 10" in gs and "mp_regen: float = 1.000" in gs


def test_every_ability_slot_carries_a_cost_key(project):
    """A missing key defaults to free, so the key must always be present -- this is the
    shape check that would have caught the cost regression without an engine run."""
    import re
    runner = (project / "scripts" / "ability_runner.gd").read_text(encoding="utf-8")
    table = re.search(r"const ABILITIES: Array = (\[.*?\])\n", runner, re.S).group(1)
    slots = json.loads(table)
    assert slots, "no ability slots baked"
    for slot in slots:
        assert "cost" in slot, slot


def test_hud_shows_the_new_state(project):
    hud = (project / "scripts" / "hud.gd").read_text(encoding="utf-8")
    assert "Game.mp_changed.connect" in hud
    assert "Game.equipped_changed.connect" in hud
    assert "slot_status()" in hud                      # per-slot ability readout
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    for node in ("MpLabel", "GearLabel", "AbilityLabel"):
        assert f'name="{node}"' in main, node


def test_player_can_actually_fight_back(project):
    """Before this, the player had no attack at all and enemy `hp` was exported but
    never read by anything — you could only be hurt by walking into things."""
    gd = (project / "scripts" / "player.gd").read_text(encoding="utf-8")
    assert 'Input.is_action_just_pressed("attack")' in gd
    assert "func _swing()" in gd
    # damage is asked of Game.atk() per swing, not baked, so gear can change it
    assert "take_damage(Game.atk())" in gd
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
    # + 1 ability sprite (the firebolt's shot)
    assert len(pngs) == 21
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
def test_gear_and_cost_verified_in_engine(project):
    """The claims string checks cannot make: equipping actually raises the swing, an
    ability actually charges its resource, and a kill actually produces loot. The cost
    check is what caught `cost` never being baked into the slot table."""
    from meristem_verifier.assertions import derive_assertions
    from meristem_verifier.runner import run_assertions
    wanted = {"gear_bonus", "ability_cost", "loot_drop", "tile_collision"}
    asserts = [a for a in derive_assertions(SpecStore.load(MANIFEST).get_all())
               if a["kind"] in wanted]
    assert {a["kind"] for a in asserts} == wanted, asserts
    res = run_assertions(project, asserts, os.environ["MERISTEM_GODOT"])
    assert res["ok"], res


@pytest.mark.skipif(not os.environ.get("MERISTEM_GODOT"),
                    reason="set MERISTEM_GODOT to a Godot 4.x binary to run the engine smoke test")
def test_ability_damage_verified_in_engine(project):
    """A projectile ability has the most moving parts of any: its own scene, a launch
    handoff, travel, and a collision. Checking the generated script for the right
    strings proves none of that connects."""
    from meristem_verifier.assertions import derive_assertions
    from meristem_verifier.runner import run_assertions
    asserts = [a for a in derive_assertions(SpecStore.load(MANIFEST).get_all())
               if a["kind"] == "ability_damage"]
    assert asserts, "no ability_damage assertion derived for a player with a projectile"
    res = run_assertions(project, asserts, os.environ["MERISTEM_GODOT"])
    assert res["ok"], res


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
