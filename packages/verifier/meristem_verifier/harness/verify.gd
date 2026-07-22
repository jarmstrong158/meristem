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

func _write(obj: Dictionary) -> void:
	var wf: FileAccess = FileAccess.open("res://verifier/results.json", FileAccess.WRITE)
	wf.store_string(JSON.stringify(obj))
	wf.close()
