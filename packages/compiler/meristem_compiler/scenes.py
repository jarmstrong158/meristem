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
##
## `level_name` is set per scene rather than baked into this script, so one shared
## world.gd serves every room instead of a near-identical copy per level.

const TILE: int = 16

@export var level_name: String = ""

func _ready() -> void:
	if level_name == "":
		push_warning("Ground.level_name is empty; no ground to build")
		return
	var f: FileAccess = FileAccess.open("res://levels/%s.grid.json" % level_name, FileAccess.READ)
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


GAME_STATE_GD = '''extends Node
## Global run state (autoloaded as "Game"): hp, the ability resource, collected items
## and what they equip. Death resets the run and reloads the level.
##
## Effective stats live HERE rather than baked as constants into the player script,
## because gear changes them at runtime: the player asks for atk() every swing.

signal hp_changed(hp: int, max_hp: int)
signal mp_changed(mp: int, max_mp: int)
signal collected(item_id: String, total: int)
signal equipped_changed(slot: String, item_id: String)
signal enemy_killed(total: int)

## id -> {slot, stats}, baked from the manifest's items domain. The runtime needs the
## stats to apply a bonus and the slot to know where the thing is worn.
const ITEMS: Dictionary = {{items}}
## Only these slots are WORN. A consumable or key_item is carried and grants nothing,
## which is why equipping is slot-driven rather than "anything with stats".
const EQUIP_SLOTS: Array = ["weapon", "armor", "accessory"]

var max_hp: int = {{max_hp}}
var hp: int = {{max_hp}}
var base_atk: int = {{base_atk}}
var base_def: int = {{base_def}}
var max_mp: int = {{max_mp}}
## float so a fractional regen can accumulate across frames; readers see int(mp)
var mp: float = float({{max_mp}})
var mp_regen: float = {{mp_regen}}
var items: Dictionary = {}
var equipped: Dictionary = {}
var kills: int = 0

func _process(delta: float) -> void:
	if mp_regen <= 0.0 or mp >= float(max_mp):
		return
	# only signal when the DISPLAYED value changes, not every frame
	var before: int = int(mp)
	mp = minf(mp + mp_regen * delta, float(max_mp))
	if int(mp) != before:
		mp_changed.emit(int(mp), max_mp)

## Spend the ability resource. Returns false when it cannot be paid, so the caller can
## decline to fire AND decline to burn a cooldown.
func spend(cost: int) -> bool:
	if cost <= 0:
		return true
	if int(mp) < cost:
		return false
	mp -= float(cost)
	mp_changed.emit(int(mp), max_mp)
	return true

## --- gear ---
func stat_bonus(stat: String) -> int:
	var total: int = 0
	for slot in equipped:
		var entry: Dictionary = ITEMS.get(equipped[slot], {})
		var stats: Dictionary = entry.get("stats", {})
		total += int(stats.get(stat, 0))
	return total

func atk() -> int:
	return maxi(base_atk + stat_bonus("atk"), 1)

func defense() -> int:
	return maxi(base_def + stat_bonus("def"), 0)

func _try_equip(item_id: String) -> void:
	var entry: Dictionary = ITEMS.get(item_id, {})
	var slot: String = str(entry.get("slot", ""))
	if not EQUIP_SLOTS.has(slot):
		return
	equipped[slot] = item_id
	equipped_changed.emit(slot, item_id)

## Where the player should appear in the room it is walking INTO. change_scene_to_file
## cannot carry arguments, and this autoload is the only thing that survives the swap,
## so a door leaves the arrival cell here and the player picks it up in _ready. Null
## means "use wherever the scene already placed the player".
var _pending_spawn: Variant = null

func register_kill() -> void:
	kills += 1
	enemy_killed.emit(kills)

func set_pending_spawn(spawn: Vector2) -> void:
	_pending_spawn = spawn

func go_to_room(scene_path: String, spawn: Vector2) -> void:
	set_pending_spawn(spawn)
	get_tree().change_scene_to_file(scene_path)

## Read-once: a stale arrival cell must not teleport the player again on the next
## reload after a death.
func take_pending_spawn() -> Variant:
	var p: Variant = _pending_spawn
	_pending_spawn = null
	return p

func take_damage(amount: int) -> void:
	# defence subtracts, but a hit always lands for at least 1: enough armour would
	# otherwise make the player invulnerable and the game unlosable
	hp = clampi(hp - maxi(amount - defense(), 1), 0, max_hp)
	hp_changed.emit(hp, max_hp)
	if hp <= 0:
		_restart()

func heal(amount: int) -> void:
	hp = clampi(hp + amount, 0, max_hp)
	hp_changed.emit(hp, max_hp)

func collect(item_id: String) -> void:
	items[item_id] = int(items.get(item_id, 0)) + 1
	# picking something up wears it, if it is the kind of thing you wear
	_try_equip(item_id)
	var total: int = 0
	for k in items:
		total += int(items[k])
	collected.emit(item_id, total)

func _restart() -> void:
	hp = max_hp
	mp = float(max_mp)
	items = {}
	equipped = {}
	kills = 0
	_pending_spawn = null
	hp_changed.emit(hp, max_hp)
	mp_changed.emit(int(mp), max_mp)
	get_tree().call_deferred("reload_current_scene")
'''

PROJECTILE_GD = '''extends Area2D
## A travelling shot fired by a `projectile` ability. speed/power/range are baked per
## ability by the compiler; direction comes from whoever launched it.

@export var speed: float = 120.0
@export var power: int = 1
@export var max_range: float = 120.0

var _dir: Vector2 = Vector2.RIGHT
var _travelled: float = 0.0

func launch(from: Vector2, dir: Vector2) -> void:
	global_position = from
	_dir = dir.normalized() if dir.length() > 0.0 else Vector2.RIGHT

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _physics_process(delta: float) -> void:
	var step: float = speed * delta
	global_position += _dir * step
	_travelled += step
	if _travelled >= max_range:
		queue_free()

func _on_body_entered(body: Node2D) -> void:
	if not body.is_in_group("enemies"):
		return
	if body.has_method("take_damage"):
		body.take_damage(power)
	queue_free()
'''

ABILITY_RUNNER_GD = '''extends Node
## The player's ability slots. A separate component rather than part of the controller
## template, so abilities are not tied to one control scheme and a second controller
## does not need its own copy of this.
##
## ABILITIES is baked by the compiler from the manifest, in the entity's declared
## order, and each slot binds to the ability_<n> input action. Every `kind` in the
## fixed library is implemented here; the compiler refuses a kind it cannot emit, so
## the match below can never fall through to an unknown one.

const ABILITIES: Array = {{abilities}}

var _cooldowns: Array = []

func _ready() -> void:
	_cooldowns.resize(ABILITIES.size())
	_cooldowns.fill(0.0)

func _process(delta: float) -> void:
	for i in range(_cooldowns.size()):
		_cooldowns[i] = maxf(_cooldowns[i] - delta, 0.0)

func ready_slot(slot: int) -> bool:
	return slot >= 0 and slot < ABILITIES.size() and _cooldowns[slot] <= 0.0

## What each slot is doing right now, for the HUD. Public so the readout does not have
## to reach into the cooldown array.
func slot_status() -> Array:
	var out: Array = []
	for i in range(ABILITIES.size()):
		out.append({"id": str(ABILITIES[i].get("id", "")), "cooldown": _cooldowns[i],
					"cost": int(ABILITIES[i].get("cost", 0))})
	return out

## Returns true if the ability fired, so the caller can tell "not ready" from "no such
## slot" without reaching into the cooldown array.
func use(slot: int, facing: Vector2) -> bool:
	if not ready_slot(slot):
		return false
	var a: Dictionary = ABILITIES[slot]
	# Pay FIRST, and if it cannot be paid, do not burn the cooldown either -- a failed
	# cast that still put the ability on cooldown would read as the game eating inputs.
	if not Game.spend(int(a.get("cost", 0))):
		return false
	_cooldowns[slot] = float(a.get("cooldown", 0.0))
	match str(a.get("kind", "")):
		"projectile": _fire(a, facing)
		"melee_arc": _arc(a)
		"heal": _heal(a)
		"dash": _dash(a, facing)
	return true

func _owner_body() -> Node2D:
	return get_parent() as Node2D

func _fire(a: Dictionary, facing: Vector2) -> void:
	var packed: PackedScene = load(str(a.get("scene", "")))
	if packed == null:
		return
	var shot: Area2D = packed.instantiate()
	# added to the SCENE, not to this node: a shot must outlive the caster's transform
	# and keep flying if the player moves or dies
	_owner_body().get_parent().add_child(shot)
	shot.launch(_owner_body().global_position, facing)

## Hits every enemy in reach, all round -- the difference from the basic swing is that
## it does not care which way you are facing.
func _arc(a: Dictionary) -> void:
	var reach: float = float(a.get("range", 30.0))
	var power: int = int(a.get("power", 1))
	var here: Vector2 = _owner_body().global_position
	for node in get_tree().get_nodes_in_group("enemies"):
		var enemy: Node2D = node as Node2D
		if enemy == null or not enemy.has_method("take_damage"):
			continue
		if here.distance_to(enemy.global_position) <= reach:
			enemy.take_damage(power)

func _heal(a: Dictionary) -> void:
	Game.heal(int(a.get("power", 1)))

func _dash(a: Dictionary, facing: Vector2) -> void:
	var body: Node2D = _owner_body()
	var dir: Vector2 = facing.normalized() if facing.length() > 0.0 else Vector2.RIGHT
	if body is CharacterBody2D:
		# move_and_collide so a dash cannot post the player through a wall
		(body as CharacterBody2D).move_and_collide(dir * float(a.get("power", 16.0)))
	else:
		body.global_position += dir * float(a.get("power", 16.0))
'''

DOOR_GD = '''extends Area2D
## A doorway between rooms. `to_scene` and `to_spawn` are baked per door by the
## compiler from the level's `exits`.

@export var to_scene: String = ""
@export var to_spawn: Vector2 = Vector2.ZERO

var _used: bool = false

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	# one-shot: overlapping bodies can fire twice in a frame, and a second
	# change_scene_to_file during the same transition throws the swap away
	if _used or to_scene == "" or not body.is_in_group("player"):
		return
	_used = true
	Game.go_to_room(to_scene, to_spawn)
'''

PICKUP_GD = '''extends Area2D
## A collectable item. `item_id` is baked per item type by the compiler.

@export var item_id: String = ""

func _ready() -> void:
	body_entered.connect(_on_body_entered)

func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("player"):
		Game.collect(item_id)
		queue_free()
'''

HUD_GD = '''extends CanvasLayer
## HUD: hp next to the heart, the ability resource, collected count next to the coin,
## kills, equipped gear, and per-slot ability state.

@onready var _hp_label: Label = $HpLabel
@onready var _mp_label: Label = $MpLabel
@onready var _item_label: Label = $ItemLabel
@onready var _kill_label: Label = $KillLabel
@onready var _gear_label: Label = $GearLabel
@onready var _ability_label: Label = $AbilityLabel

func _ready() -> void:
	Game.hp_changed.connect(_on_hp_changed)
	Game.mp_changed.connect(_on_mp_changed)
	Game.collected.connect(_on_collected)
	Game.equipped_changed.connect(_on_equipped_changed)
	Game.enemy_killed.connect(_on_enemy_killed)
	_on_hp_changed(Game.hp, Game.max_hp)
	_on_mp_changed(int(Game.mp), Game.max_mp)
	var total: int = 0
	for k in Game.items:
		total += int(Game.items[k])
	_item_label.text = "x %d" % total
	_on_enemy_killed(Game.kills)
	_refresh_gear()

## Polled rather than signalled: a cooldown is a continuously changing value, and a
## signal per frame per slot would be noise.
func _process(_delta: float) -> void:
	var runner: Node = _ability_runner()
	if runner == null:
		_ability_label.text = ""
		return
	var parts: Array = []
	for i in range(runner.slot_status().size()):
		var s: Dictionary = runner.slot_status()[i]
		var state: String = "rdy" if s["cooldown"] <= 0.0 else "%.1f" % s["cooldown"]
		if int(s["cost"]) > int(Game.mp):
			state = "no mp"
		parts.append("%d:%s %s" % [i + 1, s["id"], state])
	_ability_label.text = "  ".join(parts)

func _ability_runner() -> Node:
	var players: Array = get_tree().get_nodes_in_group("player")
	if players.is_empty():
		return null
	return (players[0] as Node).get_node_or_null("Abilities")

func _on_hp_changed(hp: int, max_hp: int) -> void:
	_hp_label.text = "%d/%d  atk %d  def %d" % [hp, max_hp, Game.atk(), Game.defense()]

func _on_mp_changed(mp: int, max_mp: int) -> void:
	_mp_label.text = "mp %d/%d" % [mp, max_mp]

func _on_collected(_item_id: String, total: int) -> void:
	_item_label.text = "x %d" % total

func _on_equipped_changed(_slot: String, _item_id: String) -> void:
	_refresh_gear()
	# gear moves atk/def, which the hp line shows
	_on_hp_changed(Game.hp, Game.max_hp)

func _refresh_gear() -> void:
	if Game.equipped.is_empty():
		_gear_label.text = ""
		return
	var worn: Array = []
	for slot in Game.equipped:
		worn.append("%s:%s" % [slot, Game.equipped[slot]])
	_gear_label.text = "  ".join(worn)

func _on_enemy_killed(total: int) -> void:
	_kill_label.text = "slain %d" % total
'''


def render_template(template: str, **params) -> str:
    text = (TEMPLATES / template).read_text(encoding="utf-8")
    for k, v in params.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


# Mechanics `kind` -> (controller template, the params it substitutes with defaults).
#
# This mapping is the compiler's honest statement of what it can actually emit. The
# mechanics schema offers three kinds; only the ones listed here have a template. The
# player script used to be rendered from `top_down_controller.gd.tmpl`
# UNCONDITIONALLY, so a fully valid platformer manifest — validate_all green — compiled
# "successfully" into a top-down game: jump_height and gravity were dropped on the
# floor and a FRICTION constant was invented from a default for a parameter the
# platformer schema does not even allow. Adding a controller is one entry here plus one
# template file; until then the compiler REFUSES the kind (see compile.py) rather than
# quietly building the wrong game.
CONTROLLERS: dict[str, tuple[str, dict[str, float]]] = {
    "top_down_controller": ("top_down_controller.gd.tmpl",
                            # attack_range is measured between BODY ORIGINS, and two
                            # colliding 16px actors sit ~24px apart (verified in-engine:
                            # walking into an enemy settles at 23.9). A 22px reach could
                            # therefore never hit an enemy the player was touching --
                            # the attack looked correct in the script and did nothing in
                            # the game. 30px reaches a touching enemy with margin.
                            {"move_speed": 80.0, "accel": 600.0, "friction": 400.0,
                             "attack_range": 30.0, "attack_cooldown": 0.35}),
}

# Enemy `ai` -> (template, the entity STATS it substitutes with defaults).
#
# Same shape and same discipline as CONTROLLERS: what is listed here is what the
# compiler can actually emit, and an ai it has no template for is refused rather than
# quietly downgraded to a bobbing placeholder. Tuning is read from the entity's own
# free-form `stats`, not from the mechanics archetype, because how fast one particular
# slime walks is a property of that slime and not of the control scheme.
ENEMY_AI: dict[str, tuple[str, dict[str, float]]] = {
    "idle":   ("enemy_idle.gd.tmpl", {}),
    "patrol": ("enemy_patrol.gd.tmpl", {"speed": 26.0, "patrol_distance": 40.0}),
    "chase":  ("enemy_chase.gd.tmpl", {"speed": 38.0, "aggro_radius": 90.0}),
}
DEFAULT_ENEMY_AI = "idle"

# Ability `kind`s the runner implements. Same discipline again: an unlisted kind is
# refused by the compiler rather than baked into a slot that silently does nothing when
# pressed. All of these live in ONE script (ability_runner.gd) rather than one template
# each, because a character holds several kinds at once and dispatches per slot at
# runtime -- unlike a controller, where exactly one applies.
ABILITY_KINDS = ("projectile", "melee_arc", "heal", "dash")
# How many slots the input map binds. Abilities past this compile but are unreachable,
# so the compiler says so rather than leaving the author to wonder.
ABILITY_SLOTS = 3


def _gd_literal(value) -> str:
    """A GDScript literal for a baked ability table. json.dumps is close enough for
    dicts/arrays/numbers/strings and produces valid GDScript for all of them."""
    import json
    return json.dumps(value)


def write_scripts(project_dir: Path, *, kind: str, params: dict,
                  enemies: list[dict], player_hp: int = 20,
                  player_atk: int = 1, player_def: int = 0,
                  player_mp: int = 0, player_mp_regen: float = 0.0,
                  items: dict | None = None,
                  abilities: list[dict] | None = None) -> None:
    """player.gd + world.gd + game_state.gd/pickup.gd/hud.gd/door.gd + one enemy_<id>.gd
    per enemy type (stats and ai baked in), plus the ability runner and projectile
    script when the player has abilities.

    `kind` selects the controller template; only its own declared params are
    substituted, so one controller's defaults can never leak into another's script.
    Each enemy dict is {id, name, hp, atk, ai, stats}. `abilities` is the player's
    resolved slot list, in order. `items` is id -> {slot, stats}, for gear bonuses."""
    template, defaults = CONTROLLERS[kind]
    sd = project_dir / "scripts"
    sd.mkdir(parents=True, exist_ok=True)
    slots = abilities or []
    (sd / "ability_runner.gd").write_text(
        ABILITY_RUNNER_GD.replace("{{abilities}}", _gd_literal(slots)), encoding="utf-8")
    if any(a.get("kind") == "projectile" for a in slots):
        (sd / "projectile.gd").write_text(PROJECTILE_GD, encoding="utf-8")
    (sd / "player.gd").write_text(
        render_template(template,
                        ability_slots=ABILITY_SLOTS,
                        **{key: float(params.get(key, fallback))
                           for key, fallback in defaults.items()}),
        encoding="utf-8")
    for e in enemies:
        ai_template, ai_defaults = ENEMY_AI[e.get("ai", DEFAULT_ENEMY_AI)]
        stats = e.get("stats", {}) or {}
        (sd / f"enemy_{e['id']}.gd").write_text(
            render_template(ai_template, name=e["name"], hp=int(e["hp"]), atk=int(e["atk"]),
                            **{key: float(stats.get(key, fallback))
                               for key, fallback in ai_defaults.items()}),
            encoding="utf-8")
    (sd / "world.gd").write_text(WORLD_GD, encoding="utf-8")
    (sd / "game_state.gd").write_text(
        GAME_STATE_GD
        .replace("{{max_hp}}", str(int(player_hp)))
        .replace("{{base_atk}}", str(max(1, int(player_atk))))
        .replace("{{base_def}}", str(max(0, int(player_def))))
        .replace("{{max_mp}}", str(max(0, int(player_mp))))
        .replace("{{mp_regen}}", f"{float(player_mp_regen):.3f}")
        .replace("{{items}}", _gd_literal(items or {})),
        encoding="utf-8")
    (sd / "pickup.gd").write_text(PICKUP_GD, encoding="utf-8")
    (sd / "hud.gd").write_text(HUD_GD, encoding="utf-8")
    (sd / "door.gd").write_text(DOOR_GD, encoding="utf-8")


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


def _pickup_tscn(item_id: str, texture_file: str) -> str:
    return f'''[gd_scene load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://assets/{texture_file}" id="1_tex"]
[ext_resource type="Script" path="res://scripts/pickup.gd" id="2_scr"]

[sub_resource type="RectangleShape2D" id="shape_{item_id}"]
size = Vector2(12, 12)

[node name="Pickup" type="Area2D"]
script = ExtResource("2_scr")
item_id = "{item_id}"

[node name="Sprite2D" type="Sprite2D" parent="."]
texture = ExtResource("1_tex")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("shape_{item_id}")
'''


def _projectile_tscn(ability_id: str, texture_file: str, speed: float, power: int,
                     max_range: float) -> str:
    return f'''[gd_scene load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://assets/{texture_file}" id="1_tex"]
[ext_resource type="Script" path="res://scripts/projectile.gd" id="2_scr"]

[sub_resource type="RectangleShape2D" id="shape_{ability_id}"]
size = Vector2(8, 8)

[node name="Projectile" type="Area2D"]
script = ExtResource("2_scr")
speed = {speed}
power = {power}
max_range = {max_range}

[node name="Sprite2D" type="Sprite2D" parent="."]
texture = ExtResource("1_tex")

[node name="CollisionShape2D" type="CollisionShape2D" parent="."]
shape = SubResource("shape_{ability_id}")
'''


def _player_tscn() -> str:
    # The ability runner is a child NODE rather than code in the controller script, so
    # abilities are not coupled to a control scheme; the controller only forwards input.
    return '''[gd_scene load_steps=5 format=3]

[ext_resource type="SpriteFrames" path="res://scenes/player_frames.tres" id="1_frames"]
[ext_resource type="Script" path="res://scripts/player.gd" id="2_scr"]
[ext_resource type="Script" path="res://scripts/ability_runner.gd" id="3_abil"]

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

[node name="Abilities" type="Node" parent="."]
script = ExtResource("3_abil")
'''


def _room_tscn(room: dict, heart_sprite: str, coin_ext: str, coin_node: str) -> str:
    """One room's scene. Every room is the same shape — ground, player, actors, camera,
    HUD — differing only in its grid name and placements, so they come off one builder
    instead of `main.tscn` being special."""
    p = room["placements"]
    px, py = p["player"]
    cx, cy = p["camera"]
    doors = p.get("doors", [])

    ext = ['[ext_resource type="PackedScene" path="res://scenes/player.tscn" id="1_player"]']
    enemy_rid: dict[str, str] = {}
    for sp in p.get("enemies", []):
        if sp["id"] not in enemy_rid:
            rid = f"e{len(enemy_rid)}_enemy"
            enemy_rid[sp["id"]] = rid
            ext.append(f'[ext_resource type="PackedScene" '
                       f'path="res://scenes/enemy_{sp["id"]}.tscn" id="{rid}"]')
    item_rid: dict[str, str] = {}
    for it in p.get("items", []):
        if it["id"] not in item_rid:
            rid = f"i{len(item_rid)}_item"
            item_rid[it["id"]] = rid
            ext.append(f'[ext_resource type="PackedScene" '
                       f'path="res://scenes/pickup_{it["id"]}.tscn" id="{rid}"]')
    ext.append('[ext_resource type="Script" path="res://scripts/world.gd" id="3_world"]')
    ext.append(f'[ext_resource type="Texture2D" path="res://assets/{heart_sprite}" id="4_heart"]')
    ext.append('[ext_resource type="Script" path="res://scripts/hud.gd" id="6_hud"]')
    ext.append(coin_ext)
    if doors:
        ext.append('[ext_resource type="Script" path="res://scripts/door.gd" id="7_door"]')

    sub = ('[sub_resource type="RectangleShape2D" id="RectangleShape2D_door"]\n'
           'size = Vector2(14, 14)\n') if doors else ""

    enemy_nodes = [f'[node name="Enemy{i}" parent="." instance=ExtResource("{enemy_rid[sp["id"]]}")]\n'
                   f'position = Vector2({sp["px"]}, {sp["py"]})\n'
                   for i, sp in enumerate(p.get("enemies", []))]
    item_nodes = [f'[node name="Item{i}" parent="." instance=ExtResource("{item_rid[it["id"]]}")]\n'
                  f'position = Vector2({it["px"]}, {it["py"]})\n'
                  for i, it in enumerate(p.get("items", []))]
    door_nodes = []
    for i, d in enumerate(doors):
        door_nodes.append(
            f'[node name="Door{i}" type="Area2D" parent="."]\n'
            f'position = Vector2({d["px"]}, {d["py"]})\n'
            f'script = ExtResource("7_door")\n'
            f'to_scene = "{d["to_scene"]}"\n'
            f'to_spawn = Vector2({d["sx"]}, {d["sy"]})\n\n'
            f'[node name="Shape" type="CollisionShape2D" parent="Door{i}"]\n'
            f'shape = SubResource("RectangleShape2D_door")\n')

    return f'''[gd_scene load_steps={len(ext) + (2 if doors else 1)} format=3]

{chr(10).join(ext)}

{sub}
[node name="Main" type="Node2D"]

[node name="Ground" type="Node2D" parent="."]
script = ExtResource("3_world")
level_name = "{room["level_name"]}"

[node name="Player" parent="." instance=ExtResource("1_player")]
position = Vector2({px}, {py})

{chr(10).join(enemy_nodes)}
{chr(10).join(item_nodes)}
{chr(10).join(door_nodes)}
[node name="Camera2D" type="Camera2D" parent="."]
position = Vector2({cx}, {cy})

[node name="HUD" type="CanvasLayer" parent="."]
script = ExtResource("6_hud")

[node name="Heart" type="Sprite2D" parent="HUD"]
position = Vector2(12, 12)
texture = ExtResource("4_heart")

[node name="HpLabel" type="Label" parent="HUD"]
offset_left = 22.0
offset_top = 4.0
offset_right = 80.0
offset_bottom = 20.0
theme_override_font_sizes/font_size = 8

{coin_node}

[node name="ItemLabel" type="Label" parent="HUD"]
offset_left = 22.0
offset_top = 22.0
offset_right = 80.0
offset_bottom = 38.0
theme_override_font_sizes/font_size = 8

[node name="KillLabel" type="Label" parent="HUD"]
offset_left = 22.0
offset_top = 40.0
offset_right = 100.0
offset_bottom = 56.0
theme_override_font_sizes/font_size = 8

[node name="MpLabel" type="Label" parent="HUD"]
offset_left = 120.0
offset_top = 4.0
offset_right = 200.0
offset_bottom = 20.0
theme_override_font_sizes/font_size = 8

[node name="GearLabel" type="Label" parent="HUD"]
offset_left = 120.0
offset_top = 22.0
offset_right = 300.0
offset_bottom = 38.0
theme_override_font_sizes/font_size = 8

[node name="AbilityLabel" type="Label" parent="HUD"]
offset_left = 120.0
offset_top = 40.0
offset_right = 316.0
offset_bottom = 56.0
theme_override_font_sizes/font_size = 8
'''


def write_scenes(project_dir: Path, *, player_idle: str, player_walk: list[str],
                 enemies: list[dict], heart_sprite: str, coin_frames: list[str],
                 rooms: list[dict], abilities: list[dict] | None = None) -> None:
    """`enemies`: [{id, frames: [asset files]}] — one scene per enemy type.
    `rooms`: one entry per level, the FIRST being the start (written as main.tscn):
        {scene: "main.tscn", level_name: "grove_01", placements: {...}}
    `placements`: {player:(px,py), camera:(px,py), enemies:[{id,px,py}],
                   items:[{id,file,px,py}], doors:[{px,py,to_scene,sx,sy}]} — all in
    pixels, from that level's spawn and exit markers."""
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

    # projectile scenes: one per projectile ABILITY (its sprite, speed, power and range
    # are baked), shared by every room
    for ab in abilities or []:
        if ab.get("kind") == "projectile" and ab.get("texture"):
            (sc / f"projectile_{ab['id']}.tscn").write_text(
                _projectile_tscn(ab["id"], ab["texture"], float(ab.get("speed", 120.0)),
                                 int(ab.get("power", 1)), float(ab.get("range", 120.0))),
                encoding="utf-8")

    # pickup scenes: one per item TYPE, shared by every room that places it
    for room in rooms:
        for it in room["placements"].get("items", []):
            path = sc / f"pickup_{it['id']}.tscn"
            if not path.exists():
                path.write_text(_pickup_tscn(it["id"], it["file"]), encoding="utf-8")

    for room in rooms:
        (sc / room["scene"]).write_text(
            _room_tscn(room, heart_sprite, coin_ext, coin_node), encoding="utf-8")
