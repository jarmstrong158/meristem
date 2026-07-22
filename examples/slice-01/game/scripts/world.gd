extends Node2D
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
