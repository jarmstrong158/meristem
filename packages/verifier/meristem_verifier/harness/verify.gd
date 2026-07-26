extends Node
## Assertion-loop harness. Runs under true --headless (physics works without a
## renderer). Reads res://verifier/assertions.json, runs each supported assertion
## against the compiled project, writes res://verifier/results.json, quits.

func _ready() -> void:
	var results: Array = []
	var f: FileAccess = FileAccess.open("res://verifier/assertions.json", FileAccess.READ)
	if f == null:
		_write({"error": "assertions.json not found"})
		get_tree().quit()
		return
	var parsed: Dictionary = JSON.parse_string(f.get_as_text())
	var assertions: Array = parsed.get("assertions", [])
	for a in assertions:
		var kind: String = a.get("kind", "")
		if kind == "move_speed":
			results.append(await _check_move_speed(a))
		elif kind == "melee_damage":
			results.append(await _check_melee_damage(a))
		elif kind == "ability_damage":
			results.append(await _check_ability_damage(a))
		elif kind == "room_transition":
			results.append(await _check_room_transition(a))
		else:
			results.append({"kind": kind, "ok": false, "error": "unsupported assertion"})
	_write({"results": results})
	get_tree().quit()

func _check_move_speed(a: Dictionary) -> Dictionary:
	var expected: float = float(a.get("expected", 0.0))
	var tol: float = float(a.get("tolerance", expected * 0.1))
	var scene: PackedScene = load("res://scenes/player.tscn")
	var player: CharacterBody2D = scene.instantiate()
	add_child(player)
	Input.action_press("move_right")
	for i in range(40):                       # settle to terminal velocity
		await get_tree().physics_frame
	var measured: float = player.velocity.length()
	Input.action_release("move_right")
	player.queue_free()
	return {
		"kind": "move_speed", "entity": a.get("entity", ""),
		"expected": expected, "measured": measured,
		"ok": absf(measured - expected) <= tol,
	}

## Put the player next to an enemy, press attack, and read the enemy's hp back. This
## checks the swing actually CONNECTS -- a string check on the generated script only
## proves the code was written.
func _check_melee_damage(a: Dictionary) -> Dictionary:
	var expected: int = int(a.get("expected", 0))
	var enemy_id: String = String(a.get("entity", ""))
	var player_scene: PackedScene = load("res://scenes/player.tscn")
	var enemy_scene: PackedScene = load("res://scenes/enemy_%s.tscn" % enemy_id)
	if player_scene == null or enemy_scene == null:
		return {"kind": "melee_damage", "entity": enemy_id, "ok": false,
				"error": "player or enemy scene missing"}
	var player: CharacterBody2D = player_scene.instantiate()
	var enemy: CharacterBody2D = enemy_scene.instantiate()
	add_child(player)
	add_child(enemy)
	player.global_position = Vector2.ZERO
	# just to the right and within reach; the player faces DOWN by default, so drive a
	# frame of rightward input first to turn it toward the target
	enemy.global_position = Vector2(10, 0)
	await _tap("move_right")
	var before: int = int(enemy.hp)
	await _tap("attack")
	await get_tree().physics_frame
	var measured: int = int(enemy.hp) if is_instance_valid(enemy) else 0
	var killed: bool = not is_instance_valid(enemy)
	# `separation` is the distance the bodies actually settled at once they collided.
	# Reported because it is the number that decides whether a reach is usable at all:
	# two colliding 16px actors sit ~24px apart, so a shorter reach silently never
	# connects no matter how correct the attack code looks.
	var separation: float = 0.0
	if is_instance_valid(enemy):
		separation = enemy.global_position.distance_to(player.global_position)
		enemy.queue_free()
	player.queue_free()
	return {
		"kind": "melee_damage", "entity": enemy_id,
		"expected": expected, "measured": measured, "before": before,
		"separation": separation, "killed": killed, "ok": measured == expected,
	}

## Press an ability slot and check the shot actually reaches an enemy and damages it.
## Driven through the input action, not by calling the runner directly, so the binding
## from key to slot is part of what is proven.
func _check_ability_damage(a: Dictionary) -> Dictionary:
	var expected: int = int(a.get("expected", 0))
	var enemy_id: String = str(a.get("entity", ""))
	var slot: int = int(a.get("slot", 0))
	var player_scene: PackedScene = load("res://scenes/player.tscn")
	var enemy_scene: PackedScene = load("res://scenes/enemy_%s.tscn" % enemy_id)
	if player_scene == null or enemy_scene == null:
		return {"kind": "ability_damage", "ok": false, "error": "player or enemy scene missing"}
	var player: CharacterBody2D = player_scene.instantiate()
	var enemy: CharacterBody2D = enemy_scene.instantiate()
	add_child(player)
	add_child(enemy)
	player.global_position = Vector2.ZERO
	# well outside melee reach, so a hit can only come from the ability
	enemy.global_position = Vector2(64, 0)
	enemy.set_physics_process(false)          # hold it still; chasers would close in
	await _tap("move_right")                  # turn to face the target
	var before: int = int(enemy.hp)
	await _tap("ability_%d" % (slot + 1))
	# let the shot travel: 64px at the authored speed takes well under half a second
	for _i in range(40):
		await get_tree().physics_frame
		if not is_instance_valid(enemy) or int(enemy.hp) != before:
			break
	var measured: int = int(enemy.hp) if is_instance_valid(enemy) else 0
	if is_instance_valid(enemy):
		enemy.queue_free()
	player.queue_free()
	return {
		"kind": "ability_damage", "ability": a.get("ability", ""), "slot": slot,
		"expected": expected, "measured": measured, "before": before,
		"ok": measured == expected,
	}

## Every door in a room must point at a scene that LOADS, and its arrival cell must
## actually move an arriving player. Deliberately does not call change_scene_to_file:
## that would replace this harness mid-run and throw the results away. The scene swap
## itself is engine behaviour; the baked res:// path and the arrival handoff are ours,
## and a wrong path is invisible until someone walks into the doorway.
func _check_room_transition(a: Dictionary) -> Dictionary:
	var from_scene: String = str(a.get("from_scene", "res://scenes/main.tscn"))
	var packed: PackedScene = load(from_scene)
	if packed == null:
		return {"kind": "room_transition", "ok": false, "error": "start scene did not load"}
	var room: Node = packed.instantiate()
	add_child(room)
	await get_tree().physics_frame
	var checks: Array = []
	var all_ok: bool = true
	for child in room.get_children():
		if not (child is Area2D):
			continue
		var raw_target: Variant = child.get("to_scene")
		if raw_target == null:
			continue                       # not a door (pickups are Area2D too)
		var target_path: String = str(raw_target)
		if target_path == "":
			continue
		var arrival: Vector2 = child.get("to_spawn") as Vector2
		var loads: bool = load(target_path) != null
		var spawn_applied: bool = false
		if loads:
			Game.set_pending_spawn(arrival)
			var pl: Node = load("res://scenes/player.tscn").instantiate()
			add_child(pl)
			await get_tree().physics_frame
			spawn_applied = (pl as Node2D).global_position.distance_to(arrival) < 1.0
			pl.queue_free()
		checks.append({"to": target_path, "loads": loads, "spawn_applied": spawn_applied})
		all_ok = all_ok and loads and spawn_applied
	room.queue_free()
	if checks.is_empty():
		return {"kind": "room_transition", "ok": false, "error": "no doors found in scene"}
	return {"kind": "room_transition", "doors": checks, "ok": all_ok}

## Hold an action across TWO physics frames, then release.
##
## One frame is not enough. Input.action_press() lands mid-frame, so a listener polling
## Input.is_action_just_pressed() in _physics_process can miss the window entirely if
## its callback already ran for that frame -- and releasing immediately closes it. That
## made the ability check pass only when other assertions had run first and warmed up
## the frame counter: green in a full run, red on its own.
func _tap(action: String) -> void:
	Input.action_press(action)
	await get_tree().physics_frame
	await get_tree().physics_frame
	Input.action_release(action)

func _write(obj: Dictionary) -> void:
	var wf: FileAccess = FileAccess.open("res://verifier/results.json", FileAccess.WRITE)
	wf.store_string(JSON.stringify(obj))
	wf.close()
