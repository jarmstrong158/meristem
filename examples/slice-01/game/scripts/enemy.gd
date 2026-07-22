extends CharacterBody2D
## Generated enemy 'Grove Slime'. Vertical-slice placeholder behavior: idle bob.
## Real AI archetypes come later; the manifest already carries its stats.

@export var hp: int = 8
@export var atk: int = 2

var _t: float = 0.0
var _home_y: float = 0.0

func _ready() -> void:
	_home_y = position.y

func _physics_process(delta: float) -> void:
	_t += delta
	position.y = _home_y + sin(_t * 2.0) * 1.0
