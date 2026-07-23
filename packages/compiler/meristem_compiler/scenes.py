"""Emit Godot 4.6 scenes + scripts from templates. GDScript uses explicit types
(Godot 4.6 strict typing). The ground is built at runtime from the compiler-emitted
grid JSON so the slice runs with zero addons; the .ldtk remains the canonical level."""
from __future__ import annotations

from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"

WORLD_GD = '''extends Node2D
## Builds the ground from the compiler-emitted level grid. The .ldtk file
## (levels/) is the canonical, LDtk-editable level; this runtime builder lets the
## vertical slice run without the godot-ldtk-importer addon.

const TILE: int = 16

func _ready() -> void:
	var f: FileAccess = FileAccess.open("res://levels/{{level}}.grid.json", FileAccess.READ)
	if f == null:
		push_warning("level grid not found")
		return
	var data: Dictionary = JSON.parse_string(f.get_as_text())
	var grid: Array = data.get("grid", [])
	for y in range(grid.size()):
		var row: Array = grid[y]
		for x in range(row.size()):
			var tname: String = row[x]
			if tname == "":
				continue
			var tex: Texture2D = load("res://assets/tile_%s.png" % tname)
			if tex == null:
				continue
			var s: Sprite2D = Sprite2D.new()
			s.texture = tex
			s.centered = false
			s.position = Vector2(x * TILE, y * TILE)
			add_child(s)
'''


def render_template(template: str, **params) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    for k, v in params.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def write_scripts(project_dir: Path, *, move_speed, accel, friction,
                  enemies: list[dict], level_name: str = "grove_01") -> None:
    """player.gd + world.gd + one enemy_<id>.gd per enemy type (stats baked in)."""
    sd = project_dir / "scripts"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "player.gd").write_text(
        render_template("top_down_controller.gd.tmpl",
                        move_speed=float(move_speed), accel=float(accel), friction=float(friction)),
        encoding="utf-8")
    for e in enemies:
        (sd / f"enemy_{e['id']}.gd").write_text(
            render_template("enemy_idle.gd.tmpl", name=e["name"], hp=int(e["hp"]), atk=int(e["atk"])),
            encoding="utf-8")
    (sd / "world.gd").write_text(WORLD_GD.replace("{{level}}", level_name), encoding="utf-8")


def _actor_tscn(node_name: str, sprite_path: str, script_path: str,
                shape_id: str, shape_size: tuple[int, int]) -> str:
    return f'''[gd_scene load_steps=4 format=3]

[ext_resource type="Texture2D" path="{sprite_path}" id="1_tex"]
[ext_resource type="Script" path="{script_path}" id="2_scr"]

[sub_resource type="RectangleShape2D" id="{shape_id}"]
size = Vector2({shape_size[0]}, {shape_size[1]})

[node name="{node_name}" type="CharacterBody2D"]
script = ExtResource("2_scr")

[node name="Sprite2D" type="Sprite2D" parent="."]
offset = Vector2(0, -16)
texture = ExtResource("1_tex")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
position = Vector2(0, -8)
shape = SubResource("{shape_id}")
'''


def _frames_tres(anims: list[tuple[str, list[str], float]]) -> str:
    """A SpriteFrames resource holding one or more named looping animations.
    `anims` is a list of (animation_name, [texture_files], speed)."""
    textures: list[str] = []
    for _, frs, _ in anims:
        for t in frs:
            if t not in textures:
                textures.append(t)
    idx = {t: i + 1 for i, t in enumerate(textures)}
    ext = "".join(
        f'[ext_resource type="Texture2D" path="res://assets/{t}" id="{idx[t]}_f"]\n'
        for t in textures)
    blocks = []
    for name, frs, speed in anims:
        fr = ", ".join(f'{{"duration": 1.0, "texture": ExtResource("{idx[t]}_f")}}' for t in frs)
        blocks.append(f'{{\n"frames": [{fr}],\n"loop": true,\n"name": &"{name}",\n"speed": {speed}\n}}')
    return f'''[gd_resource type="SpriteFrames" load_steps={len(textures) + 1} format=3]

{ext}
[resource]
animations = [{", ".join(blocks)}]
'''


def _animated_actor_tscn(node_name: str, frames_path: str, script_path: str,
                         shape_id: str, shape_size: tuple[int, int], anim: str = "idle") -> str:
    return f'''[gd_scene load_steps=4 format=3]

[ext_resource type="SpriteFrames" path="{frames_path}" id="1_frames"]
[ext_resource type="Script" path="{script_path}" id="2_scr"]

[sub_resource type="RectangleShape2D" id="{shape_id}"]
size = Vector2({shape_size[0]}, {shape_size[1]})

[node name="{node_name}" type="CharacterBody2D"]
script = ExtResource("2_scr")

[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]
offset = Vector2(0, -16)
sprite_frames = ExtResource("1_frames")
animation = &"{anim}"
autoplay = "{anim}"

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
position = Vector2(0, -8)
shape = SubResource("{shape_id}")
'''


def _player_tscn() -> str:
    return '''[gd_scene load_steps=4 format=3]

[ext_resource type="SpriteFrames" path="res://scenes/player_frames.tres" id="1_frames"]
[ext_resource type="Script" path="res://scripts/player.gd" id="2_scr"]

[sub_resource type="RectangleShape2D" id="RectangleShape2D_player"]
size = Vector2(10, 16)

[node name="Player" type="CharacterBody2D"]
script = ExtResource("2_scr")

[node name="AnimatedSprite2D" type="AnimatedSprite2D" parent="."]
offset = Vector2(0, -16)
sprite_frames = ExtResource("1_frames")
animation = &"idle"
autoplay = "idle"

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
position = Vector2(0, -8)
shape = SubResource("RectangleShape2D_player")
'''


def write_scenes(project_dir: Path, *, player_idle: str, player_walk: list[str],
                 enemies: list[dict], heart_sprite: str, coin_frames: list[str],
                 placements: dict) -> None:
    """`enemies`: [{id, frames: [asset files]}] — one scene per enemy type.
    `placements`: {player: (px,py), enemies: [{id,px,py}], items: [{file,px,py}],
                   camera: (px,py)} — all in pixels, from the level's spawn markers."""
    sc = project_dir / "scenes"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "player_frames.tres").write_text(
        _frames_tres([("idle", [player_idle], 5.0), ("walk", player_walk, 8.0)]), encoding="utf-8")
    (sc / "player.tscn").write_text(_player_tscn(), encoding="utf-8")

    # One scene per enemy TYPE: AnimatedSprite2D when the archetype animates, else static.
    for e in enemies:
        eid, frames = e["id"], e["frames"]
        if len(frames) > 1:
            (sc / f"enemy_{eid}_frames.tres").write_text(
                _frames_tres([("idle", frames, 6.0)]), encoding="utf-8")
            (sc / f"enemy_{eid}.tscn").write_text(
                _animated_actor_tscn("Enemy", f"res://scenes/enemy_{eid}_frames.tres",
                                     f"res://scripts/enemy_{eid}.gd",
                                     f"RectangleShape2D_{eid}", (14, 10)), encoding="utf-8")
        else:
            (sc / f"enemy_{eid}.tscn").write_text(
                _actor_tscn("Enemy", f"res://assets/{frames[0]}", f"res://scripts/enemy_{eid}.gd",
                            f"RectangleShape2D_{eid}", (14, 10)), encoding="utf-8")

    # HUD coin: a spinning AnimatedSprite2D when it has a spin cycle, else static.
    if len(coin_frames) > 1:
        (sc / "coin_frames.tres").write_text(
            _frames_tres([("spin", coin_frames, 8.0)]), encoding="utf-8")
        coin_ext = '[ext_resource type="SpriteFrames" path="res://scenes/coin_frames.tres" id="5_coin"]'
        coin_node = ('[node name="Coin" type="AnimatedSprite2D" parent="HUD"]\n'
                     'position = Vector2(12, 30)\n'
                     'sprite_frames = ExtResource("5_coin")\n'
                     'animation = &"spin"\n'
                     'autoplay = "spin"')
    else:
        coin_ext = f'[ext_resource type="Texture2D" path="res://assets/{coin_frames[0]}" id="5_coin"]'
        coin_node = ('[node name="Coin" type="Sprite2D" parent="HUD"]\n'
                     'position = Vector2(12, 30)\n'
                     'texture = ExtResource("5_coin")')

    # ext resources: one PackedScene per enemy type, one Texture2D per item file
    enemy_ext, item_ext = [], []
    enemy_scene_id = {}
    for i, e in enumerate(enemies):
        rid = f"e{i}_enemy"
        enemy_scene_id[e["id"]] = rid
        enemy_ext.append(f'[ext_resource type="PackedScene" path="res://scenes/enemy_{e["id"]}.tscn" id="{rid}"]')
    item_tex_id = {}
    for i, it in enumerate(placements.get("items", [])):
        if it["file"] not in item_tex_id:
            rid = f"i{i}_item"
            item_tex_id[it["file"]] = rid
            item_ext.append(f'[ext_resource type="Texture2D" path="res://assets/{it["file"]}" id="{rid}"]')

    px, py = placements["player"]
    cx, cy = placements["camera"]
    enemy_nodes = []
    for i, sp in enumerate(placements.get("enemies", [])):
        enemy_nodes.append(f'[node name="Enemy{i}" parent="." instance=ExtResource("{enemy_scene_id[sp["id"]]}")]\n'
                           f'position = Vector2({sp["px"]}, {sp["py"]})\n')
    item_nodes = []
    for i, it in enumerate(placements.get("items", [])):
        item_nodes.append(f'[node name="Item{i}" type="Sprite2D" parent="."]\n'
                          f'position = Vector2({it["px"]}, {it["py"]})\n'
                          f'texture = ExtResource("{item_tex_id[it["file"]]}")\n')

    load_steps = 4 + len(enemy_ext) + len(item_ext)
    (sc / "main.tscn").write_text(f'''[gd_scene load_steps={load_steps} format=3]

[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1_player"]
{chr(10).join(enemy_ext)}
[ext_resource type="Script" path="res://scripts/world.gd" id="3_world"]
[ext_resource type="Texture2D" path="res://assets/{heart_sprite}" id="4_heart"]
{coin_ext}
{chr(10).join(item_ext)}

[node name="Main" type="Node2D"]

[node name="Ground" type="Node2D" parent="."]
script = ExtResource("3_world")

[node name="Player" parent="." instance=ExtResource("1_player")]
position = Vector2({px}, {py})

{chr(10).join(enemy_nodes)}
{chr(10).join(item_nodes)}
[node name="Camera2D" type="Camera2D" parent="."]
position = Vector2({cx}, {cy})

[node name="HUD" type="CanvasLayer" parent="."]

[node name="Heart" type="Sprite2D" parent="HUD"]
position = Vector2(12, 12)
texture = ExtResource("4_heart")

{coin_node}
''', encoding="utf-8")
