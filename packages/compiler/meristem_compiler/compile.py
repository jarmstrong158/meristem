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
from .level import synthesize_grove
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

    # 1. assets (generate + gate + provenance)
    written = compile_assets(domains, out / "assets")

    # 2. level -> .ldtk (canonical) + tileset + runtime grid
    grid = synthesize_grove()
    ldtk_info = write_ldtk(grid, out / "assets", out / "levels")

    # 3. scripts + scenes
    archetype = _archetype_for(domains, project["control_scheme"])
    params = archetype.get("params", {})
    player = domains["entities"]["characters"][0]
    enemy = domains["entities"]["enemies"][0]
    write_scripts(out,
                  move_speed=params.get("move_speed", 80),
                  accel=params.get("accel", 600),
                  friction=params.get("friction", 400),
                  enemy_name=enemy["name"], enemy_hp=int(enemy["stats"].get("hp", 1)),
                  enemy_atk=int(enemy["stats"].get("atk", 1)))
    write_scenes(out,
                 player_sprite=asset_filename(contract, "character", player["sprite"], "idle"),
                 enemy_sprite=asset_filename(contract, "enemy", enemy["sprite"], "idle"),
                 heart_sprite="ui_heart.png", coin_sprite="ui_coin.png")

    # 4. project.godot
    write_project_godot(out, name=project["title"], main_scene="res://scenes/main.tscn",
                        width=project["target_resolution"]["w"],
                        height=project["target_resolution"]["h"],
                        archetype_kind=archetype["kind"])

    return {"project_dir": str(out), "assets": len(written), "level": ldtk_info,
            "title": project["title"]}
