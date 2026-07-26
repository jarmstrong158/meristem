"""Orchestrate: manifest -> Godot 4 project on disk. Deterministic, no LLM.

Refuses to compile an invalid manifest (validate_all must pass first)."""
from __future__ import annotations

from pathlib import Path

from asset_gate.contract import StyleContract
from asset_gate.naming import asset_filename
from meristem_spec_store import SpecStore

from .assets import compile_assets
from .godot_project import write_project_godot
from .ldtk import write_ldtk
from .level import grid_from_level, pick_level, synthesize_grove
from .scenes import (ABILITY_KINDS, ABILITY_SLOTS, CONTROLLERS, DEFAULT_ENEMY_AI,
                     ENEMY_AI, write_scenes, write_scripts)


class CompileError(RuntimeError):
    pass


def _archetype_for(domains: dict, control_scheme: str) -> dict:
    for a in domains.get("mechanics", {}).get("archetypes", []):
        if a["id"] == control_scheme:
            return a
    raise CompileError(f"control_scheme {control_scheme!r} has no matching mechanics archetype")


def _controller_kind(archetype: dict) -> str:
    """The archetype's kind, refused loudly if the compiler has no template for it.

    The manifest is not wrong here — the mechanics schema legitimately offers
    platformer_controller and turn_based_combat, and a spec may describe one before the
    compiler can build it. What was wrong is compiling anyway: the player script was
    rendered from the top-down template regardless of kind, so a platformer produced a
    game with no gravity and no jump and reported success. Refusing is the honest
    outcome, and it names what IS available so the author can act."""
    kind = archetype.get("kind")
    if kind not in CONTROLLERS:
        raise CompileError(
            f"mechanics archetype {archetype.get('id')!r} has kind {kind!r}, which this "
            f"compiler cannot emit yet — implemented: {sorted(CONTROLLERS)}. The manifest "
            f"itself is valid; this is a compiler gap, not a spec error. Compiling anyway "
            f"would silently produce a {sorted(CONTROLLERS)[0]!r} game and discard this "
            f"archetype's params.")
    return kind


def _player_abilities(domains: dict, player: dict, item_files: dict) -> list[dict]:
    """The player's ability slots, in declared order, flattened for baking.

    Refuses a kind the runner cannot execute, for the same reason as a controller or an
    ai: a slot bound to an unimplemented kind would be pressable and silently do
    nothing. Slots past what the input map binds are also called out, because an
    unreachable ability is a spec that does not do what it says."""
    by_id = {a["id"]: a for a in (domains.get("abilities", {}) or {}).get("abilities", [])}
    slots: list[dict] = []
    refs = player.get("abilities", [])
    if len(refs) > ABILITY_SLOTS:
        raise CompileError(
            f"character {player.get('id')!r} declares {len(refs)} abilities but only "
            f"{ABILITY_SLOTS} input slots exist (ability_1..ability_{ABILITY_SLOTS}); "
            f"the extras would be unreachable")
    for ref in refs:
        ab = by_id.get(ref)
        if ab is None:                       # cross-ref catches this; belt and braces
            raise CompileError(f"character {player.get('id')!r} references ability "
                               f"{ref!r} which is not defined")
        if ab["kind"] not in ABILITY_KINDS:
            raise CompileError(
                f"ability {ref!r} has kind {ab['kind']!r}, which this compiler cannot "
                f"emit yet -- implemented: {sorted(ABILITY_KINDS)}. The manifest is "
                f"valid; this is a compiler gap, not a spec error.")
        slot = {"id": ab["id"], "kind": ab["kind"], "power": ab["power"],
                "cooldown": ab.get("cooldown", 0.0)}
        if ab.get("range") is not None:
            slot["range"] = ab["range"]
        if ab["kind"] == "projectile":
            slot["speed"] = ab.get("speed", 120.0)
            slot["scene"] = f"res://scenes/projectile_{ab['id']}.tscn"
            texture = item_files.get(f"ability_{ab['id']}")
            if texture is None:
                raise CompileError(f"projectile ability {ref!r} has no generated sprite")
            slot["texture"] = texture
        slots.append(slot)
    return slots


def _enemy_ai(entity: dict) -> str:
    """The enemy's ai archetype, refused loudly if there is no template for it.

    Same rule as the controller: silently falling back to the placeholder would give
    an author a stationary bobbing blob where they asked for a chaser, with nothing
    anywhere saying so."""
    ai = entity.get("ai", DEFAULT_ENEMY_AI)
    if ai not in ENEMY_AI:
        raise CompileError(
            f"enemy {entity.get('id')!r} has ai {ai!r}, which this compiler cannot emit "
            f"yet — implemented: {sorted(ENEMY_AI)}.")
    return ai


def compile_project(manifest_path: str | Path, out_dir: str | Path) -> dict:
    store = SpecStore.load(manifest_path)
    report = store.validate_all()
    if report.missing_domains:
        # Previously validate_all only checked the domains that were PRESENT, so an
        # empty/partial manifest passed here and died below on domains["project"]
        # with a bare KeyError. Now it fails with something an author can act on.
        raise CompileError(report.summary())
    if not report.ok:
        raise CompileError(f"manifest is invalid, refusing to compile: {report.to_dict()}")
    domains = store.get_all()

    project = domains["project"]
    contract = StyleContract.from_dict(domains["style_contract"])

    # Resolve the control scheme BEFORE doing any work. A kind the compiler cannot emit
    # is a dead end, so it should not first generate every asset and write the level.
    archetype = _archetype_for(domains, project["control_scheme"])
    controller_kind = _controller_kind(archetype)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. every authored level becomes its own room; the start comes first. Pre-domain
    # manifests still get the one synthesized grove.
    start = pick_level(domains)
    authored = (domains.get("levels", {}) or {}).get("levels", [])
    if start is not None:
        ordered = [start] + [lv for lv in authored if lv["id"] != start["id"]]
        rooms_src = [{"id": lv["id"], "grid": grid_from_level(lv),
                      "spawns": lv.get("spawns", []), "exits": lv.get("exits", []),
                      "player_cell": (lv["player_spawn"]["x"], lv["player_spawn"]["y"])}
                     for lv in ordered]
    else:
        rooms_src = [{"id": "grove_01", "grid": synthesize_grove(),
                      "spawns": [{"id": domains["entities"]["enemies"][0]["id"],
                                  "kind": "enemy", "x": 13, "y": 8}],
                      "exits": [], "player_cell": (4, 5)}]
    # the START room keeps the name main.tscn, so it stays project.godot's entry point
    scene_of = {r["id"]: ("main.tscn" if i == 0 else f"level_{r['id']}.tscn")
                for i, r in enumerate(rooms_src)}
    spawn_cell_of = {r["id"]: r["player_cell"] for r in rooms_src}
    used_tiles = tuple(sorted({c for r in rooms_src for row in r["grid"] for c in row}))

    # 2. assets (generate + gate + provenance), incl. every tile any room uses
    written = compile_assets(domains, out / "assets", extra_tiles=used_tiles)

    # 3. each level -> .ldtk (canonical) + tileset + runtime grid
    ldtk_infos = [write_ldtk(r["grid"], out / "assets", out / "levels", name=r["id"])
                  for r in rooms_src]
    ldtk_info = ldtk_infos[0]

    # 4. scripts + scenes: one enemy type per distinct spawned enemy, items placed
    params = archetype.get("params", {})
    player = domains["entities"]["characters"][0]
    enemies_by_id = {e["id"]: e for e in domains["entities"].get("enemies", [])}
    spawned_enemy_ids = sorted({s["id"] for r in rooms_src for s in r["spawns"]
                                if s["kind"] == "enemy"})
    enemy_types = [{"id": eid, "name": enemies_by_id[eid]["name"],
                    "hp": enemies_by_id[eid]["stats"].get("hp", 1),
                    "atk": enemies_by_id[eid]["stats"].get("atk", 1),
                    "ai": _enemy_ai(enemies_by_id[eid]),
                    "stats": enemies_by_id[eid]["stats"]}
                   for eid in spawned_enemy_ids]
    item_files = {w["entity"]: w["file"] for w in written if w["class"] == "item_icon"}
    ability_slots = _player_abilities(domains, player, item_files)
    write_scripts(out, kind=controller_kind, params=params, enemies=enemy_types,
                  player_hp=int(player["stats"].get("hp", 20)),
                  player_atk=int(player["stats"].get("atk", 1)),
                  abilities=ability_slots)

    def frame_files(entity_id: str, prefix: str) -> list[str]:
        return [w["file"] for w in sorted(written, key=lambda w: w.get("frame", 0))
                if w["entity"] == entity_id and (w.get("variant") or "").startswith(prefix)]

    player_walk = frame_files(player["id"], "walk_")
    coin_frames = [asset_filename(contract, "ui_element", "coin", None)] + frame_files("coin", "spin_")
    enemy_scene_data = [
        {"id": eid,
         "frames": [asset_filename(contract, "enemy", eid, "idle")] + frame_files(eid, "anim_")}
        for eid in spawned_enemy_ids]

    T = 16
    rooms = []
    for r in rooms_src:
        grid = r["grid"]
        placements = {
            "player": (r["player_cell"][0] * T + 8, r["player_cell"][1] * T + 16),
            "camera": (len(grid[0]) * T // 2, len(grid) * T // 2),
            "enemies": [{"id": s["id"], "px": s["x"] * T + 8, "py": s["y"] * T + 16}
                        for s in r["spawns"] if s["kind"] == "enemy"],
            "items": [],
            "doors": [],
        }
        for s in r["spawns"]:
            if s["kind"] != "item":
                continue
            if s["id"] not in item_files:
                raise CompileError(f"level {r['id']!r} places item {s['id']!r}, "
                                   f"but it has no sprite (give it a sprite descriptor)")
            placements["items"].append({"id": s["id"], "file": item_files[s["id"]],
                                        "px": s["x"] * T + 8, "py": s["y"] * T + 8})
        for ex in r["exits"]:
            target = ex["to"]
            if target not in scene_of:      # cross-ref catches this; belt and braces
                raise CompileError(f"level {r['id']!r} exit leads to {target!r}, "
                                   f"which is not a compiled level")
            # arrival defaults to the target room's own player_spawn
            cell = ex.get("to_spawn") or {"x": spawn_cell_of[target][0],
                                          "y": spawn_cell_of[target][1]}
            placements["doors"].append({
                "px": ex["x"] * T + 8, "py": ex["y"] * T + 8,
                "to_scene": f"res://scenes/{scene_of[target]}",
                "sx": cell["x"] * T + 8, "sy": cell["y"] * T + 16,
            })
        rooms.append({"scene": scene_of[r["id"]], "level_name": r["id"],
                      "placements": placements})

    write_scenes(out,
                 player_idle=asset_filename(contract, "character", player["id"], "idle"),
                 player_walk=player_walk,
                 enemies=enemy_scene_data,
                 heart_sprite="ui_heart.png", coin_frames=coin_frames,
                 rooms=rooms, abilities=ability_slots)

    # 4. project.godot
    write_project_godot(out, name=project["title"], main_scene="res://scenes/main.tscn",
                        width=project["target_resolution"]["w"],
                        height=project["target_resolution"]["h"],
                        archetype_kind=archetype["kind"])

    return {"project_dir": str(out), "assets": len(written), "level": ldtk_info,
            "title": project["title"],
            # carried up so the CLI can warn: this manifest compiled, but N validation
            # checks never ran, so "it compiled" is weaker than it looks
            "checks_skipped": report.checks_skipped}
