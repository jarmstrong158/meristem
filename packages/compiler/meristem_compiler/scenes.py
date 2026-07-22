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
	var f: FileAccess = FileAccess.open("res://levels/grove_01.grid.json", FileAccess.READ)
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
                  enemy_name: str, enemy_hp: int, enemy_atk: int) -> None:
    sd = project_dir / "scripts"
    sd.mkdir(parents=True, exist_ok=True)
    (sd / "player.gd").write_text(
        render_template("top_down_controller.gd.tmpl",
                        move_speed=float(move_speed), accel=float(accel), friction=float(friction)),
        encoding="utf-8")
    (sd / "enemy.gd").write_text(
        render_template("enemy_idle.gd.tmpl", name=enemy_name, hp=enemy_hp, atk=enemy_atk),
        encoding="utf-8")
    (sd / "world.gd").write_text(WORLD_GD, encoding="utf-8")


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


def write_scenes(project_dir: Path, *, player_sprite: str, enemy_sprite: str,
                 heart_sprite: str, coin_sprite: str) -> None:
    sc = project_dir / "scenes"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "player.tscn").write_text(
        _actor_tscn("Player", f"res://assets/{player_sprite}", "res://scripts/player.gd",
                    "RectangleShape2D_player", (10, 16)), encoding="utf-8")
    (sc / "enemy.tscn").write_text(
        _actor_tscn("Enemy", f"res://assets/{enemy_sprite}", "res://scripts/enemy.gd",
                    "RectangleShape2D_enemy", (14, 10)), encoding="utf-8")
    (sc / "main.tscn").write_text(f'''[gd_scene load_steps=6 format=3]

[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1_player"]
[ext_resource type="PackedScene" path="res://scenes/enemy.tscn" id="2_enemy"]
[ext_resource type="Script" path="res://scripts/world.gd" id="3_world"]
[ext_resource type="Texture2D" path="res://assets/{heart_sprite}" id="4_heart"]
[ext_resource type="Texture2D" path="res://assets/{coin_sprite}" id="5_coin"]

[node name="Main" type="Node2D"]

[node name="Ground" type="Node2D" parent="."]
script = ExtResource("3_world")

[node name="Player" parent="." instance=ExtResource("1_player")]
position = Vector2(64, 80)

[node name="Enemy" parent="." instance=ExtResource("2_enemy")]
position = Vector2(216, 128)

[node name="Camera2D" type="Camera2D" parent="."]
position = Vector2(160, 96)

[node name="HUD" type="CanvasLayer" parent="."]

[node name="Heart" type="Sprite2D" parent="HUD"]
position = Vector2(12, 12)
texture = ExtResource("4_heart")

[node name="Coin" type="Sprite2D" parent="HUD"]
position = Vector2(12, 30)
texture = ExtResource("5_coin")
''', encoding="utf-8")
