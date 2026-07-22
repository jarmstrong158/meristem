extends CharacterBody2D
## Generated from the 'top_down_controller' mechanics archetype.
## Parameters are substituted by meristem-compiler from the manifest — do not
## hand-tune here; change the manifest and recompile.

const MOVE_SPEED: float = 80.0
const ACCEL: float = 600.0
const FRICTION: float = 400.0

@onready var _anim: AnimatedSprite2D = $AnimatedSprite2D

func _physics_process(delta: float) -> void:
	var dir: Vector2 = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if dir != Vector2.ZERO:
		velocity = velocity.move_toward(dir * MOVE_SPEED, ACCEL * delta)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, FRICTION * delta)
	if _anim != null:
		if velocity.length() > 5.0:
			_anim.play("walk")
			if absf(dir.x) > 0.0:
				_anim.flip_h = dir.x < 0.0
		else:
			_anim.play("idle")
	move_and_slide()
