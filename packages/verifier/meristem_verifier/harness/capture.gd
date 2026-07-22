extends Node
## Visual-loop capture. Runs WINDOWED (real GL renderer — --headless cannot render,
## dec-0007). Instances the real main scene, lets it settle a few frames, captures the
## viewport to res://verifier/capture.png, quits.

func _ready() -> void:
	var main: PackedScene = load("res://scenes/main.tscn")
	if main == null:
		get_tree().quit()
		return
	add_child(main.instantiate())
	for i in range(6):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var img: Image = get_viewport().get_texture().get_image()
	img.save_png("res://verifier/capture.png")
	get_tree().quit()
