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
from .scenes import write_scenes, write_scripts


class CompileError(RuntimeError):
    pass


def _archetype_for(domains: dict, control_scheme: str) -> dict:
    for a in domains.get("mechanics", {}).get("archetypes", []):
        if a["id"] == control_scheme:
            return a
    raise CompileError(f"control_scheme {control_scheme!r} has no matching mechanics archetype")


def compile_project(manifest_path: str | Path, out_dir: str | Path) -> dict:
    store = SpecStore.load(manifest_path)
    report = store.validate_all()
    if not report.ok:
        raise CompileError(f"manifest is invalid, refusing to compile: {report.to_dict()}")
    domains = store.get_all()

    project = domains["project"]
    contract = StyleContract.from_dict(domains["style_contract"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. the level grid: authored in the `levels` domain, else the synthesized grove
    level = pick_level(domains)
    if level is not None:
        grid = grid_from_level(level)
        level_name = level["id"]
        spawns = level.get("spawns", [])
        player_cell = (level["player_spawn"]["x"], level["player_spawn"]["y"])
    else:
        grid = synthesize_grove()
        level_name = "grove_01"
        spawns = [{"id": domains["entities"]["enemies"][0]["id"], "kind": "enemy", "x": 13, "y": 8}]
        player_cell = (4, 5)
    used_tiles = tuple(sorted({c for row in grid for c in row}))

    # 2. assets (generate + gate + provenance), incl. any tiles the level uses
    written = compile_assets(domains, out / "assets", extra_tiles=used_tiles)

    # 3. level -> .ldtk (canonical) + tileset + runtime grid
    ldtk_info = write_ldtk(grid, out / "assets", out / "levels", name=level_name)

    # 4. scripts + scenes: one enemy type per distinct spawned enemy, items placed
    archetype = _archetype_for(domains, project["control_scheme"])
    params = archetype.get("params", {})
    player = domains["entities"]["characters"][0]
    enemies_by_id = {e["id"]: e for e in domains["entities"].get("enemies", [])}
    spawned_enemy_ids = sorted({s["id"] for s in spawns if s["kind"] == "enemy"})
    enemy_types = [{"id": eid, "name": enemies_by_id[eid]["name"],
                    "hp": enemies_by_id[eid]["stats"].get("hp", 1),
                    "atk": enemies_by_id[eid]["stats"].get("atk", 1)}
                   for eid in spawned_enemy_ids]
    write_scripts(out,
                  move_speed=params.get("move_speed", 80),
                  accel=params.get("accel", 600),
                  friction=params.get("friction", 400),
                  enemies=enemy_types, level_name=level_name,
                  player_hp=int(player["stats"].get("hp", 20)))

    def frame_files(entity_id: str, prefix: str) -> list[str]:
        return [w["file"] for w in sorted(written, key=lambda w: w.get("frame", 0))
                if w["entity"] == entity_id and (w.get("variant") or "").startswith(prefix)]

    player_walk = frame_files(player["id"], "walk_")
    coin_frames = [asset_filename(contract, "ui_element", "coin", None)] + frame_files("coin", "spin_")
    enemy_scene_data = [
        {"id": eid,
         "frames": [asset_filename(contract, "enemy", eid, "idle")] + frame_files(eid, "anim_")}
        for eid in spawned_enemy_ids]

    item_files = {w["entity"]: w["file"] for w in written if w["class"] == "item_icon"}
    T = 16
    placements = {
        "player": (player_cell[0] * T + 8, player_cell[1] * T + 16),
        "camera": (len(grid[0]) * T // 2, len(grid) * T // 2),
        "enemies": [{"id": s["id"], "px": s["x"] * T + 8, "py": s["y"] * T + 16}
                    for s in spawns if s["kind"] == "enemy"],
        "items": [],
    }
    for s in spawns:
        if s["kind"] != "item":
            continue
        if s["id"] not in item_files:
            raise CompileError(f"level {level_name!r} places item {s['id']!r}, "
                               f"but it has no sprite (give it a sprite descriptor)")
        placements["items"].append({"id": s["id"], "file": item_files[s["id"]],
                                    "px": s["x"] * T + 8, "py": s["y"] * T + 8})

    write_scenes(out,
                 player_idle=asset_filename(contract, "character", player["id"], "idle"),
                 player_walk=player_walk,
                 enemies=enemy_scene_data,
                 heart_sprite="ui_heart.png", coin_frames=coin_frames,
                 placements=placements)

    # 4. project.godot
    write_project_godot(out, name=project["title"], main_scene="res://scenes/main.tscn",
                        width=project["target_resolution"]["w"],
                        height=project["target_resolution"]["h"],
                        archetype_kind=archetype["kind"])

    return {"project_dir": str(out), "assets": len(written), "level": ldtk_info,
            "title": project["title"]}
