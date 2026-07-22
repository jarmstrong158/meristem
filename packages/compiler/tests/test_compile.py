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


def test_project_godot_written(project):
    txt = (project / "project.godot").read_text(encoding="utf-8")
    assert 'config/name="Slime Grove"' in txt
    assert 'run/main_scene="res://scenes/main.tscn"' in txt
    assert "move_up=" in txt and "move_left=" in txt          # input map present
    assert "default_texture_filter=0" in txt                  # pixel-art nearest


def test_all_assets_and_sidecars(project):
    a = project / "assets"
    pngs = sorted(p.name for p in a.glob("*.png"))
    # 9 base + 4 player-walk + 3 enemy idle-anim + 3 coin spin frames
    assert len(pngs) == 19
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
    ef = (project / "scenes" / "enemy_frames.tres").read_text(encoding="utf-8")
    assert '&"idle"' in ef and ef.count("enemy_slime_") == 4          # idle + 3 anim frames
    assert "AnimatedSprite2D" in (project / "scenes" / "enemy.tscn").read_text(encoding="utf-8")
    for i in (1, 2, 3):
        assert (project / "assets" / f"enemy_slime_anim_{i}.png").exists()
    # the HUD coin spins
    cf = (project / "scenes" / "coin_frames.tres").read_text(encoding="utf-8")
    assert '&"spin"' in cf and cf.count("ui_coin") == 4               # idle + 3 spin frames
    main = (project / "scenes" / "main.tscn").read_text(encoding="utf-8")
    assert 'type="AnimatedSprite2D" parent="HUD"' in main


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
    for ref in ("player.tscn", "enemy.tscn", "world.gd", "ui_heart.png"):
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


def test_archetype_enum_matches_registry():
    # the schema's sprite-archetype enum must stay in sync with the generator registry
    from meristem_generators import known_archetypes
    from meristem_spec_store.schemas import find_schema_dir
    sdir = find_schema_dir()
    reg = set(known_archetypes())
    for f in ("entities.schema.json", "items.schema.json"):
        schema = json.loads((sdir / f).read_text(encoding="utf-8"))
        enum = set(schema["$defs"]["sprite"]["properties"]["archetype"]["enum"])
        assert enum == reg, f"{f} archetype enum drift: {enum ^ reg}"


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
def test_godot_imports_and_runs(project):
    godot = os.environ["MERISTEM_GODOT"]
    imp = subprocess.run([godot, "--headless", "--path", str(project), "--import"],
                         capture_output=True, text=True, timeout=120)
    assert imp.returncode == 0, imp.stderr
    run = subprocess.run([godot, "--headless", "--path", str(project), "--quit-after", "5"],
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    assert "SCRIPT ERROR" not in (run.stdout + run.stderr)
